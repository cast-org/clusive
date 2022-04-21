import json
import logging

from dateutil.parser import parse as dateutil_parse
from dateutil.relativedelta import relativedelta
from django.http import JsonResponse
from django.utils import timezone
from django.views import View

from .models import Message
from eventlog.models import Event

logger = logging.getLogger(__name__)

def process_messages(queue_timestamp, messages, user, request):
    client_reported_time = dateutil_parse(queue_timestamp)
    delta = get_delta_from_now(client_reported_time)

    for message in messages:
        message_username = message["username"]
        session_username = user.username
        if(message_username != session_username):
            logger.debug("Rejected individual message, message username %s did not match session username %s ",
                         message_username, session_username)
            continue
        message_timestamp = adjust_message_timestamp(message["timestamp"], delta)
        message_content = message["content"]

        message_type = message["content"]["type"]
        new_message = Message(message_type, message_timestamp, message_content, request)
        try:
            new_message.send_signal()
        except Exception as e:
            logger.warning('Failed to process item from message queue. Exception: %s; item: %s' % (e, new_message))

def adjust_message_timestamp(timestamp, delta):
    message_time = dateutil_parse(timestamp)
    adjusted_message_time = message_time+delta
    message_timestamp = adjusted_message_time.isoformat()

    return message_timestamp

def get_delta_from_now(compare_time):
    now = timezone.now()
    return relativedelta(now, compare_time)

class MessageQueueView(View):
    def post(self, request):
        try:
            if request.headers.get('Content-Type').startswith('multipart/form-data'):
                receivedQueue = request.POST.dict()
                receivedQueue['messages'] = json.loads(receivedQueue['messages'])
            else:
                receivedQueue = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning('Received malformed message queue: %s' % request.body)
            return JsonResponse(status=501, data={'message': 'Invalid JSON in request body'})
        logger.debug("Received a message queue: %s" % receivedQueue)

        clusive_user = request.clusive_user
        if clusive_user is None:
            logger.warning('Rejected message queue, no current session')
            return JsonResponse(status=501, data={'message': 'No current session'})

        queue_timestamp = receivedQueue["timestamp"]
        queue_username = receivedQueue["username"]
        messages = receivedQueue["messages"]
        username = clusive_user.user.username
        if queue_username == username:
            process_messages(queue_timestamp, messages, clusive_user.user, request)
        else:
            logger.debug("Rejected message queue, queue username %s did not match session username %s ",
                         queue_username, username)
            return JsonResponse(status=501, data={'message': 'Invalid user'})
        return JsonResponse({'success': 1})

    def get(self, request, *args, **kwargs):
        """
        Was the message persisted?  Check using the event id.
        """
        event_id = "unknown id" # safe since real ids are UUIDs.
        try:
            event_id = kwargs['event_id']
            the_event = Event.objects.get(id=event_id)
        except:
            logger.warning('Event %s not found', event_id)
            return JsonResponse(status=501, data={'message': 'No such event'})
        return JsonResponse({'success': 1})

