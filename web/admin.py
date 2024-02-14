from django.contrib import admin
from .models import DataLeak, SensitiveDataPattern

# Register your models here.


@admin.register(DataLeak)
class DataLeakAdmin(admin.ModelAdmin):
    list_display = ('id', 'pattern', 'content', 'message_id', 'message')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('pattern')


@admin.register(SensitiveDataPattern)
class DataLeakPatternAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'pattern')

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        return super().save_model(request, obj, form, change)
