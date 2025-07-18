# Generated by Django 5.2.3 on 2025-07-04 22:22

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='foto_perfil',
            field=models.ImageField(blank=True, help_text='Sube una imagen para tu foto de perfil (máximo 5MB)', null=True, upload_to='perfiles/', verbose_name='Foto de Perfil'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='descripcion_corta',
            field=models.TextField(blank=True, help_text='Cuéntanos un poco sobre ti', max_length=255, null=True, verbose_name='Descripción Corta'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='email',
            field=models.EmailField(max_length=254, unique=True, verbose_name='Correo Electrónico'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='fecha_registro',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Fecha de Registro'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='telefono',
            field=models.CharField(blank=True, max_length=15, null=True, verbose_name='Teléfono'),
        ),
        migrations.AlterModelTable(
            name='usuario',
            table=None,
        ),
    ]
