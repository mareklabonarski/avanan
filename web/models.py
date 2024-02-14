import re

from django.core.exceptions import ValidationError
from django.db import models

# Create your models here.


def validate_regex_group(value):
    if '(' not in value or ')' not in value:
        raise ValidationError(
            "%(value)s does not contain a regex group - regex wrapped in ()",
            params={"value": value},
        )


class SensitiveDataPattern(models.Model):
    name = models.CharField(max_length=32)
    pattern = models.CharField(max_length=128, validators=[validate_regex_group])

    _compiled = None

    def __str__(self):
        return self.name

    @property
    def compiled(self):
        if self._compiled is None:
            self._compiled = re.compile(self.pattern, re.DOTALL)
        return self._compiled

    # Visa ^4[0-9]{3} [0-9]{4} [0-9]{4} (?:[0-9]{4})?$


class DataLeak(models.Model):
    pattern = models.ForeignKey(SensitiveDataPattern, on_delete=models.CASCADE)
    content = models.CharField(max_length=1024)
    message = models.TextField()
    message_id = models.UUIDField()

    def __str__(self):
        return f'{self.pattern.name}: {self.content}'

    class Meta:
        unique_together = ('pattern', 'message_id')
