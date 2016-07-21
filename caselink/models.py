from django.db import models
from django.core.exceptions import ValidationError


def test_pattern_match(pattern, casename):
    """
    Test if a autocase match with the name pattern.
    """
    segments = pattern.split('..')
    items = casename.split('.')
    idx = 0
    for segment in segments:
        seg_items = segment.split('.')
        try:
            while True:
                idx = items.index(seg_items[0])
                if items[idx:len(seg_items)] == seg_items:
                    items = items[len(seg_items):]
                    break
                else:
                    del items[0]
        except ValueError:
            return False
    return True


class Error(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    message = models.CharField(max_length=255, blank=True)
    def __str__(self):
        return self.id + ":" + self.message


class Arch(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    def __str__(self):
        return self.name


class Component(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    def __str__(self):
        return self.name


class Framework(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    components = models.ManyToManyField(Component)
    def __str__(self):
        return self.name


class Project(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    def __str__(self):
        return self.name


class Document(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    components = models.ManyToManyField(Component)
    title = models.CharField(max_length=65535)
    def __str__(self):
        return self.id


class Bug(models.Model):
    """
    Linked with AutoCase through AutoCasesFailure for better autocase failure matching,
    Linked with ManualCase directly.
    """
    id = models.CharField(max_length=255, primary_key=True)
    manualcases = models.ManyToManyField('WorkItem', blank=True, related_name='bugs')

    @property
    def autocases(self):
        cases = []
        for failure in self.autocase_failures.all():
            cases += failure.autocases.all()
        return cases


    def __str__(self):
        return self.id


class WorkItem(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    type = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=65535, blank=True)
    automation = models.CharField(max_length=255, default='notautomated', blank=True)
    commit = models.CharField(max_length=255, blank=True)
    project = models.ForeignKey(Project, blank=True, null=True, related_name='workitems')
    archs = models.ManyToManyField(Arch, blank=True, related_name='workitems')
    documents = models.ManyToManyField(Document, blank=True, related_name='workitems')
    errors = models.ManyToManyField(Error, blank=True, related_name='workitems')

    #Field used to perform runtime error checking
    error_related = models.ManyToManyField('self', blank=True)

    def __str__(self):
        return self.id


    def get_related(self):
        """Get related objects for error cheking"""
        return (
            list(self.error_related.all()) +
            list(self.caselinks.all())
        )


    def error_check(self, depth=1):
        if depth > 0:
            # error_related may change, so check it first
            for item in self.error_related.all():
                item.error_check(depth - 1)

        self.error_related.clear()
        self.errors.clear()

        cases_duplicate = WorkItem.objects.filter(title=self.title)
        if len(cases_duplicate) > 1:
            self.errors.add("WORKITEM_TITLE_DUPLICATE")
            for case in cases_duplicate:
                if case == self:
                    continue
                self.error_related.add(case)

        links = CaseLink.objects.filter(workitem=self)

        if len(links) > 1:
            self.errors.add("WORKITEM_MULTI_PATTERN")

        if len(links) == 0:
            if self.automation != 'noautomated':
                self.errors.add("WORKITEM_AUTOMATION_INCONSISTENCY")
        else:
            if self.automation != 'automated':
                self.errors.add("WORKITEM_AUTOMATION_INCONSISTENCY")

            for link in links:
                if link.title != self.title:
                    self.errors.add("WORKITEM_TITLE_INCONSISTENCY")

        if depth > 0:
            for item in self.get_related():
                item.error_check(depth - 1)

        self.save()


class AutoCase(models.Model):
    id = models.CharField(max_length=65535, primary_key=True)
    archs = models.ManyToManyField(Arch, blank=True, related_name='autocases')
    framework = models.ForeignKey(Framework, null=True, on_delete=models.PROTECT,
                                  related_name='autocases')
    start_commit = models.CharField(max_length=255, blank=True)
    end_commit = models.CharField(max_length=255, blank=True)
    errors = models.ManyToManyField(Error, blank=True, related_name='autocases')

    #Field used to perform runtime error checking
    #error_related = models.ManyToManyField('self', blank=True)


    def get_related(self):
        """Get related objects for error cheking"""
        return (
            list(self.caselinks.all())
        )


    def __str__(self):
        return self.id


    def autolink(self):
        for link in CaseLink.objects.all():
            if link.test_match(self):
                link.autocases.add(self)
                link.save()


    def error_check(self, depth=1):
        self.errors.clear()

        if len(self.caselinks.all()) < 1:
            self.errors.add("NO_WORKITEM")

        if len(self.caselinks.all()) > 1:
            self.errors.add("MULTIPLE_WORKITEM")

        if depth > 0:
            for item in self.get_related():
                item.error_check(depth - 1)

        self.save()


class CaseLink(models.Model):
    workitem = models.ForeignKey(WorkItem, on_delete=models.PROTECT, related_name='caselinks')
    autocases = models.ManyToManyField(AutoCase, blank=True, related_name='caselinks')
    autocase_pattern = models.CharField(max_length=255)
    framework = models.ForeignKey(Framework, on_delete=models.PROTECT, null=True,
                                  related_name='caselinks')
    errors = models.ManyToManyField(Error, blank=True, related_name='caselinks')

    #Field used to perform runtime error checking
    error_related = models.ManyToManyField('self', blank=True)

    # Legacy
    title = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("workitem", "autocase_pattern",)


    def test_match(self, auto_case):
        """
        Test if a autocase match with the name pattern.
        """
        return test_pattern_match(self.autocase_pattern, auto_case.id)


    def autolink(self):
        for case in AutoCase.objects.all():
            if self.test_match(case):
                self.autocases.add(case)
        self.save()


    def get_related(self):
        """Get related objects for error cheking"""
        return (
            list(self.error_related.all()) +
            list([self.workitem]) +
            list(self.autocases.all())
        )


    def error_check(self, depth=1):
        if depth > 0:
            for item in self.error_related.all():
                item.error_check(depth - 1)
        self.error_related.clear()
        self.errors.clear()

        links_duplicate = CaseLink.objects.filter(autocase_pattern=self.autocase_pattern)

        if len(self.autocases.all()) < 1:
            self.errors.add("PATTERN_INVALID")

        if len(links_duplicate) > 1:
            self.errors.add("PATTERN_DUPLICATE")
            for link in links_duplicate:
                if link == self:
                    continue
                self.error_related.add(link)

        if depth > 0:
            for item in self.get_related():
                item.error_check(depth - 1)

        self.save()


class AutoCaseFailure(models.Model):
    autocases = models.ManyToManyField(AutoCase, related_name="failures")
    type = models.CharField(max_length=255)
    bug = models.ForeignKey('Bug', related_name='autocase_failures', blank=True)
    failure_regex = models.CharField(max_length=65535)
    autocase_pattern = models.CharField(max_length=255)


    class Meta:
        unique_together = ("failure_regex", "autocase_pattern",)


    def clean(self):
        if self.type not in ['BUG', 'CASE-UPDATE']:
            raise ValidationError(_('Unsupported AutoCase Failure Type' + str(self.type)))
        if self.type == 'BUG' and not self.bug:
            raise ValidationError(_('Bug id required.'))


    def test_match(self, auto_case):
        """
        Test if a autocase match with the name pattern.
        """
        return test_pattern_match(self.autocase_pattern, auto_case.id)


    def autolink(self):
        for case in AutoCase.objects.all():
            if self.test_match(case):
                self.autocases.add(case)
        self.save()


    def __str__(self):
        return self.autocase_pattern

