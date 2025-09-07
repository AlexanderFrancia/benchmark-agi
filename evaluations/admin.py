from django.contrib import admin

from .runs import EvaluationRun, EvaluationResult

admin.site.register(EvaluationRun)
admin.site.register(EvaluationResult)

