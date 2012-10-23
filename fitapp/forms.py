from django import forms

from . import utils


INPUT_FORMATS = ['%Y-%m-%d']


class PeriodForm(forms.Form):
    """Data necessary to request Fitbit data from a period of time."""
    base_date = forms.DateField(input_formats=INPUT_FORMATS, required=False)
    period = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        super(PeriodForm, self).__init__(*args, **kwargs)
        PERIOD_CHOICES = [(p, p) for p in utils.get_valid_periods()]
        self.fields['period'].choices = PERIOD_CHOICES

    def get_fitbit_data(self):
        if self.is_valid():
            return {
                'base_date': self.cleaned_data['base_date'] or 'today',
                'period': self.cleaned_data['period'],
            }


class RangeForm(forms.Form):
    """Data necessary to request Fitbit data from a specific time range."""
    base_date = forms.DateField(input_formats=INPUT_FORMATS)
    end_date = forms.DateField(input_formats=INPUT_FORMATS)

    def get_fitbit_data(self):
        if self.is_valid():
            return {
                'base_date': self.cleaned_data['base_date'],
                'end_date': self.cleaned_data['end_date'],
            }
