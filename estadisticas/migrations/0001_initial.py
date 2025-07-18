# Generated by Django 5.2.3 on 2025-07-07 01:03

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EstadisticaUsuario',
            fields=[
                ('id_estadistica', models.AutoField(primary_key=True, serialize=False)),
                ('tipo_grafico', models.CharField(choices=[('BARRAS', 'Gráfico de Barras'), ('LINEA', 'Gráfico de Línea'), ('CIRCULAR', 'Gráfico Circular'), ('AREA', 'Gráfico de Área')], max_length=50)),
                ('promedio_gastos', models.DecimalField(decimal_places=2, max_digits=10)),
                ('periodo', models.CharField(choices=[('SEMANAL', 'Semanal'), ('MENSUAL', 'Mensual'), ('ANUAL', 'Anual')], max_length=20)),
                ('fecha_generacion', models.DateTimeField(default=django.utils.timezone.now)),
                ('datos_json', models.JSONField(default=dict)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Estadística de Usuario',
                'verbose_name_plural': 'Estadísticas de Usuarios',
            },
        ),
        migrations.CreateModel(
            name='Reporte',
            fields=[
                ('id_reporte', models.AutoField(primary_key=True, serialize=False)),
                ('formato', models.CharField(choices=[('PDF', 'PDF'), ('EXCEL', 'Excel'), ('CSV', 'CSV')], max_length=10)),
                ('tipo_reporte', models.CharField(choices=[('MENSUAL', 'Reporte Mensual'), ('ANUAL', 'Reporte Anual'), ('PERSONALIZADO', 'Reporte Personalizado')], max_length=20)),
                ('fecha_inicio', models.DateField()),
                ('fecha_fin', models.DateField()),
                ('fecha_generacion', models.DateTimeField(default=django.utils.timezone.now)),
                ('archivo_path', models.CharField(blank=True, max_length=500, null=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Reporte',
                'verbose_name_plural': 'Reportes',
                'ordering': ['-fecha_generacion'],
            },
        ),
    ]
