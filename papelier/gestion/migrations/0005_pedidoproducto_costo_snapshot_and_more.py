# Generated by Django 5.1.6 on 2025-02-08 00:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0004_insumo_stock'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedidoproducto',
            name='costo_snapshot',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=10),
        ),
        migrations.AddField(
            model_name='pedidoproducto',
            name='precio_snapshot',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=10),
        ),
    ]
