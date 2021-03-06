import datetime
import json
import urllib
import uuid

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.signing import TimestampSigner
from django.db import models
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render


class PagePreview(models.Model):
    token = models.CharField(max_length=255, unique=True)
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    content_json = models.TextField()
    created_at = models.DateField(auto_now_add=True)

    def as_page(self):
        content = json.loads(self.content_json)
        page_model = ContentType.objects.get_for_id(content['content_type']).model_class()
        page = page_model.from_json(self.content_json)
        page.pk = content['pk']
        return page

    @classmethod
    def garbage_collect(cls):
        yesterday = datetime.datetime.now() - datetime.timedelta(hours=24)
        cls.objects.filter(created_at__lt=yesterday).delete()


class HeadlessPreviewMixin:
    @classmethod
    def get_preview_signer(cls):
        return TimestampSigner(salt='headlesspreview.token')

    def create_page_preview(self):
        if self.pk is None:
            identifier = "parent_id=%d;page_type=%s" % (self.get_parent().pk, self._meta.label)
        else:
            identifier = "id=%d" % self.pk

        return PagePreview.objects.create(
            token=self.get_preview_signer().sign(identifier),
            content_type=self.content_type,
            content_json=self.to_json(),
        )

    @classmethod
    def get_preview_url(cls, token):
        return f'{settings.PREVIEW_URL}?' + urllib.parse.urlencode({
            'content_type': cls._meta.app_label + '.' + cls.__name__.lower(),
            'token': token,
        })

    def serve_preview(self, request, mode_name):
        page_preview = self.create_page_preview()
        page_preview.save()
        PagePreview.garbage_collect()

        return render(request, 'headlesspreview/preview.html', {
            'preview_url': self.get_preview_url(page_preview.token),
        })

    @classmethod
    def get_page_from_preview_token(cls, token):
        content_type = ContentType.objects.get_for_model(cls)

        # Check token is valid
        cls.get_preview_signer().unsign(token)

        try:
            return PagePreview.objects.get(content_type=content_type, token=token).as_page()
        except PagePreview.DoesNotExist:
            return
