# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-07-07 15:50


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('torchbox', '0043_auto_20160707_1648'),
    ]

    operations = [
        migrations.AddField(
            model_name='aboutpage',
            name='heading',
            field=models.TextField(blank=True),
        ),
    ]
