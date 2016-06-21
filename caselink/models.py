from django.db import models


class Error(models.Model):
    name = models.CharField(max_length=255)
    def __str__(self):
        return self.name


class WorkItem(models.Model):
    wi_id = models.CharField(max_length=255, primary_key=True)
    title = models.CharField(
        max_length=65535,
        blank=True,
    )
    type = models.CharField(
        max_length=255,
        blank=True,
    )
    automation = models.CharField(
        max_length=255,
        default='notautomated',
        blank=True,
    )
    feature = models.CharField(
        max_length=255,
        default='',
        blank=True,
    )
    comment = models.CharField(
        max_length=65535,
        default='',
        blank=True,
    )
    confirmed = models.DateTimeField(
        blank=True,
        null=True,
    )
    updated = models.DateTimeField(
        blank=True,
        null=True,
    )
    errors = models.ManyToManyField(Error)

    def __str__(self):
        return self.wi_id



class Document(models.Model):
    doc_id = models.CharField(max_length=65535)
    workitems = models.ManyToManyField(WorkItem)


class Change(models.Model):
    workitem = models.ForeignKey(WorkItem)
    revision = models.IntegerField()
    obj = models.CharField(max_length=65535)
    diff = models.CharField(max_length=65535)


class AvocadoCase(models.Model):
    workitems = models.ManyToManyField(WorkItem)
    name = models.CharField(max_length=65535, primary_key = True)


class TCMSCase(models.Model):
    workitems = models.ManyToManyField(WorkItem)
    tcmsid = models.CharField(max_length=255)
