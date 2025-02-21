from django.db import models
from django.db.models import Sum


class Insumo(models.Model):
    nombre = models.CharField(max_length=100)
    cantidad_total = models.PositiveIntegerField(help_text="Cantidad total recibida (ej. 500 hojas)")
    stock = models.PositiveIntegerField(default=0, help_text="Stock actual disponible")
    precio_total = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio total pagado por la cantidad recibida")
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=4, editable=False, default=0)

    class Meta:
        verbose_name_plural = "Insumos"
        ordering = ['nombre']

    def save(self, *args, **kwargs):
        if self.cantidad_total > 0:
            self.costo_unitario = self.precio_total / self.cantidad_total
            # Si es una nueva instancia, inicializa el stock con la cantidad_total.
            if not self.pk and (self.stock is None or self.stock == ''):
                self.stock = self.cantidad_total
        else:
            self.costo_unitario = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} - {self.cantidad_total} unidades"


class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    insumos = models.ManyToManyField(Insumo, through='ProductoInsumo')
    margen_ganancia = models.DecimalField(max_digits=5, decimal_places=2, help_text="Porcentaje de ganancia")
    costo_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)

    class Meta:
        verbose_name_plural = "Productos"
        ordering = ['nombre']

    def calcular_precios(self):
        # Acceder correctamente a los insumos a través de ProductoInsumo
        costo = sum(pi.insumo.costo_unitario * pi.cantidad for pi in self.productoinsumo_set.all())
        self.costo_total = costo
        self.precio_venta = costo * (1 + self.margen_ganancia / 100)
        self.save()

    def __str__(self):
        return self.nombre


class ProductoInsumo(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)


class Pedido(models.Model):
    ESTADOS = (
        ('NUEVO', 'Nuevo'),
        ('PRODUCCION', 'En Producción'),
        ('TERMINADO', 'Terminado'),
        ('ENTREGADO', 'Entregado'),
        ('CANCELADO', 'Cancelado'),
    )

    cliente_nombre = models.CharField(max_length=100)
    cliente_telefono = models.CharField(max_length=20)
    cliente_email = models.EmailField(blank=True, null=True)
    cliente_instagram = models.CharField(max_length=100, blank=True, null=True)

    productos = models.ManyToManyField('Producto', through='PedidoProducto')

    total_costo = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    total_cobrado = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    ajuste = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Nuevo campo para ajuste

    ganancia = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)

    estado = models.CharField(max_length=20, choices=ESTADOS, default='NUEVO')
    fecha = models.DateTimeField(auto_now_add=True)

    def calcular_totales(self):
        """Recalcula costos y ganancias con los snapshots de los productos en el pedido."""
        total_costo = sum(item.costo_snapshot * item.cantidad for item in self.pedidoproducto_set.all())
        total_cobrado = sum(item.precio_snapshot * item.cantidad for item in self.pedidoproducto_set.all())

        self.total_costo = total_costo
        self.total_cobrado = total_cobrado
        self.ganancia = total_cobrado - total_costo
        self.save()

    def calcular_total_a_pagar(self):
        """Calcula el total a pagar sumando el ajuste al total cobrado."""
        return self.total_cobrado + self.ajuste

    def calcular_total_pagado(self):
        """Suma todos los pagos realizados al pedido."""
        return self.pagos.aggregate(total=Sum("valor"))["total"] or 0

    def calcular_restante(self):
        """Calcula cuánto falta por pagar en el pedido."""
        return self.calcular_total_a_pagar() - self.calcular_total_pagado()

    def estado_pago(self):
        """Devuelve un estado amigable del pago."""
        restante = self.calcular_restante()
        if restante > 0:
            return f"FALTA PAGO ${restante:.2f}"
        return "PAGO COMPLETO"

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente_nombre}"



class PedidoProducto(models.Model):
    """Registra los productos en el pedido con un snapshot de precio y costo."""
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    # Captura del precio y costo en el momento de la venta
    precio_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    costo_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)

    def save(self, *args, **kwargs):
        """Guarda el precio y costo en el momento de agregar el producto al pedido."""
        if not self.id:  # Solo tomar snapshot si es un nuevo registro
            self.precio_snapshot = self.producto.precio_venta
            self.costo_snapshot = self.producto.costo_total
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto} x {self.cantidad} (Pedido {self.pedido.id})"


class PagoPedido(models.Model):
    """Modelo para registrar los pagos de los pedidos."""
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="pagos")
    fecha = models.DateTimeField(auto_now_add=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    banco = models.CharField(max_length=100)

    def __str__(self):
        return f"Pago de ${self.valor:.2f} en {self.banco} (Pedido {self.pedido.id})"


