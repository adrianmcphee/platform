from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from apps.common.fields import Base58UUIDv5Field

class AttachmentAbstract(models.Model):
    attachments = models.ManyToManyField("product_management.FileAttachment", blank=True)

    class Meta:
        abstract = True

class TreeNode(models.Model):
    id = Base58UUIDv5Field(primary_key=True)
    path = models.TextField(db_index=True)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    def save(self, *args, **kwargs):
        if self.parent:
            self.path = f"{self.parent.path}/{self.id}"
        else:
            self.path = self.id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.path})"

    @classmethod
    def get_root_nodes(cls):
        return cls.objects.filter(parent__isnull=True)

    def get_children(self):
        return self.children.all()

    def get_descendants(self, include_self=False):
        if include_self:
            return self.__class__.objects.filter(path__startswith=self.path)
        return self.__class__.objects.filter(path__startswith=f"{self.path}/")

    def get_ancestors(self, include_self=False):
        if include_self:
            return self.__class__.objects.filter(path__in=self.path.split('/'))
        return self.__class__.objects.filter(path__in=self.path.split('/')[:-1])

    def get_siblings(self, include_self=False):
        if self.parent:
            siblings = self.parent.children.all()
            if not include_self:
                siblings = siblings.exclude(id=self.id)
            return siblings
        return self.__class__.objects.filter(parent__isnull=True).exclude(id=self.id)

    def is_root(self):
        return self.parent is None

    def is_leaf(self):
        return not self.children.exists()

    def get_root(self):
        return self.get_ancestors().first() or self

    def get_depth(self):
        return len(self.path.split('/'))

    @classmethod
    def get_tree(cls, root=None):
        if root:
            return root.get_descendants(include_self=True)
        return cls.objects.all()

    def move(self, target_parent):
        old_path = self.path
        self.parent = target_parent
        self.save()
        for descendant in self.get_descendants():
            descendant.path = descendant.path.replace(old_path, self.path, 1)
            descendant.save()

    class Meta:
        abstract = True
        ordering = ['path']
        indexes = [
            models.Index(fields=['path']),
        ]