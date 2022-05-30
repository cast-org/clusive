import datetime

from django import forms


class EventLogReportForm(forms.Form):
    start_date = forms.DateField(initial=datetime.date.today()-datetime.timedelta(days=30))
    end_date = forms.DateField(initial=datetime.date.today)
