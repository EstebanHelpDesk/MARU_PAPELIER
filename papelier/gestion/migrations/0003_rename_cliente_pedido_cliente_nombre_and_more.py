# Generated by Django 5.1.6 on 2025-02-07 23:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0002_alter_pedido_ganancia_alter_pedido_total_cobrado_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='pedido',
            old_name='cliente',
            new_name='cliente_nombre',
        ),
        migrations.AddField(
            model_name='pedido',
            name='cliente_email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AddField(
            model_name='pedido',
            name='cliente_instagram',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='pedido',
            name='cliente_telefono',
            field=models.CharField(default='', max_length=20),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='pedido',
            name='estado',
            field=models.CharField(choices=[('NUEVO', 'Nuevo'), ('EN_PRODUCCION', 'En Producción'), ('TERMINADO', 'Terminado'), ('ENTREGADO', 'Entregado')], default='NUEVO', max_length=20),
        ),
    ]
