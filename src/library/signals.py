import logging
import os
import shutil

from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from eventlog.signals import vocab_lookup, translation_action, control_used
from library.models import BookVersion, Book, Paradata

logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=BookVersion) # Has to be before delete since we need access to related models
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


@receiver(vocab_lookup)
def record_vocab_lookup(sender, **kwargs):
    """Record word lookups in Paradata"""
    # Lookups can happen with no book - eg from the Wordbank. Ignore those.
    if kwargs['book']:
        Paradata.record_word_looked_up(user=kwargs['request'].clusive_user, book=kwargs['book'], word=kwargs['word'])


@receiver(translation_action)
def record_translation(sender, **kwargs):
    if kwargs['book']:
        Paradata.record_translation(user=kwargs['request'].clusive_user, book=kwargs['book'])


@receiver(control_used)
def record_read_aloud(sender, **kwargs):
    # This method is only interested in tts-play events that happen in the content of a book.
    if kwargs['event_type'] == 'TOOL_USE_EVENT' and kwargs['action'] == 'USED' and kwargs['control'] == 'tts-play':
        if kwargs['reader_info'] and kwargs['reader_info'].get('publication'):
            book_id_str = kwargs['reader_info'].get('publication').get('id')
            logger.debug('TTS PLAY book_id=%s', book_id_str)
            if book_id_str:
                book = Book.objects.get(pk=int(book_id_str))
                Paradata.record_read_aloud(book, kwargs['request'].clusive_user)
