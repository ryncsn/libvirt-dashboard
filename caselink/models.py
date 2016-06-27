from django.db import models


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
    def __str__(self):
        return self.id


class AutoCase(models.Model):
    id = models.CharField(max_length=65535, primary_key=True)
    archs = models.ManyToManyField(Arch, blank=True, related_name='autocases')
    framework = models.ForeignKey(Framework, null=True, on_delete=models.PROTECT,
                                  related_name='autocases')
    start_commit = models.CharField(max_length=255, blank=True)
    end_commit = models.CharField(max_length=255, blank=True)
    errors = models.ManyToManyField(Error, blank=True, related_name='autocases')
    def __str__(self):
        return self.id


class CaseLink(models.Model):
    workitem = models.OneToOneField(WorkItem, on_delete=models.PROTECT,
                                 primary_key=True, related_name='caselink')
    autocases = models.ManyToManyField(AutoCase, blank=True, related_name='caselinks')
    autocase_pattern = models.CharField(max_length=255, blank=True)
    framework = models.ForeignKey(Framework, on_delete=models.PROTECT, null=True,
                                  related_name='caselinks')
    errors = models.ManyToManyField(Error, blank=True, related_name='caselinks')


    # Legacy
    title = models.CharField(max_length=255, blank=True)
