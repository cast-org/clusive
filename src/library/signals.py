import logging
import os
import shutil

from django.db.models.signals import post_delete
from django.dispatch import receiver

from library.models import BookVersion, Book

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=BookVersion)
def delete_bookversion_files(sender, **kwargs):
    """When BookVersion is deleted, also delete its uploaded files"""
    instance : BookVersion
    instance = kwargs['instance']
    logger.debug('BV was deleted, cleaning up files: %s', instance)
    if os.path.exists(instance.storage_dir):
        shutil.rmtree(instance.storage_dir)


@receiver(post_delete, sender=Book)
def delete_book_files(sender, **kwargs):
    """When Book is deleted, also delete its uploaded files"""
    instance : Book
    instance = kwargs['instance']
    logger.debug('Book was deleted, cleaning up files: %s', instance)
    if os.path.exists(instance.storage_dir):
        shutil.rmtree(instance.storage_dir)
