from django.db.models import Sum, F, ExpressionWrapper, FloatField
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, FileResponse
from django.contrib import messages
from django.utils.timezone import now
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import calendar
import json
from .models import Insumo, Producto, Pedido, PedidoProducto, PagoPedido
from .forms import InsumoForm, ProductoForm, PedidoForm,PagoPedidoForm
from .models import ProductoInsumo





def home(request):
    ultimos_pedidos = Pedido.objects.exclude(estado="ENTREGADO").order_by("-fecha")[:15]
    insumos_bajos = Insumo.objects.annotate(
        threshold=ExpressionWrapper(F("cantidad_total") * 0.1, output_field=FloatField())
    ).filter(stock__lt=F("threshold"))
    
    return render(
        request, "gestion/home.html",
        {"ultimos_pedidos": ultimos_pedidos, "insumos_bajos": insumos_bajos}
    )

def listar_insumos(request):
    insumos = Insumo.objects.all()
    return render(request, "gestion/listar_insumos.html", {"insumos": insumos})


def agregar_insumo(request):
    if request.method == "POST":
        form = InsumoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Insumo agregado correctamente.")
            return redirect("listar_insumos")
    else:
        form = InsumoForm()
    return render(request, "gestion/agregar_insumo.html", {"form": form})


def editar_insumo(request, insumo_id):
    insumo = get_object_or_404(Insumo, id=insumo_id)
    
    if request.method == "POST":
        form = InsumoForm(request.POST, instance=insumo)
        if form.is_valid():
            form.save()
            messages.success(request, "Insumo actualizado correctamente.")
            return redirect("listar_insumos")
    else:
        form = InsumoForm(instance=insumo)
    return render(
        request, "gestion/editar_insumo.html", {"form": form, "insumo": insumo}
    )


def eliminar_insumo(request, insumo_id):
    insumo = get_object_or_404(Insumo, id=insumo_id)
    if request.method == "POST":
        insumo.delete()
        messages.success(request, "Insumo eliminado correctamente.")
        return redirect("listar_insumos")
    return render(request, "gestion/eliminar_insumo.html", {"insumo": insumo})


def listar_productos(request):
    productos = Producto.objects.prefetch_related("insumos", "productoinsumo_set").all()
    return render(request, "gestion/listar_productos.html", {"productos": productos})


def agregar_producto(request):
    if request.method == "POST":
        producto_form = ProductoForm(request.POST)
        if producto_form.is_valid():
            producto = producto_form.save(commit=False)
            producto.save()

            # Obtener insumos seleccionados y sus cantidades
            insumo_ids = request.POST.getlist("insumo")
            cantidades = request.POST.getlist("cantidad")

            for insumo_id, cantidad in zip(insumo_ids, cantidades):
                if cantidad and insumo_id:
                    try:
                        cantidad = float(cantidad)
                        if cantidad > 0:  # ✅ Solo guardar si la cantidad es mayor a 0
                            insumo = Insumo.objects.get(id=int(insumo_id))
                            ProductoInsumo.objects.create(
                                producto=producto, insumo=insumo, cantidad=cantidad
                            )
                    except (Insumo.DoesNotExist, ValueError):
                        pass  # Ignorar si el insumo no existe o la cantidad no es válida

            producto.calcular_precios()
            messages.success(request, "Producto agregado correctamente.")
            return redirect("listar_productos")
    else:
        producto_form = ProductoForm()

    # Asegurarse de que se pasan los insumos al template
    insumos = Insumo.objects.all()
    return render(
        request,
        "gestion/agregar_producto.html",
        {"producto_form": producto_form, "insumos": insumos},
    )


def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == "POST":
        producto_form = ProductoForm(request.POST, instance=producto)
        if producto_form.is_valid():
            producto = producto_form.save(commit=False)
            producto.save()

            # Obtener insumos seleccionados y sus cantidades
            insumo_ids = request.POST.getlist("insumo")
            cantidades = request.POST.getlist("cantidad")

            insumo_cantidades = {
                int(insumo_id): float(cant)
                for insumo_id, cant in zip(insumo_ids, cantidades)
                if cant and float(cant) > 0  # ✅ Solo considerar cantidades mayores a 0
            }

            # Eliminar insumos no seleccionados o con cantidad 0
            producto.productoinsumo_set.exclude(
                insumo_id__in=insumo_cantidades.keys()
            ).delete()

            # Agregar o actualizar insumos seleccionados
            for insumo_id, cantidad in insumo_cantidades.items():
                insumo = Insumo.objects.get(id=insumo_id)
                producto_insumo, created = ProductoInsumo.objects.get_or_create(
                    producto=producto, insumo=insumo
                )
                producto_insumo.cantidad = cantidad
                producto_insumo.save()

            producto.calcular_precios()
            messages.success(
                request, f'Producto "{producto.nombre}" actualizado correctamente.'
            )
            return redirect("listar_productos")
        else:
            messages.error(request, "Hubo un error al actualizar el producto.")

    else:
        producto_form = ProductoForm(instance=producto)
        insumos_existentes = producto.productoinsumo_set.all()

    insumos = Insumo.objects.all()
    insumos_dict = {pi.insumo.id: float(pi.cantidad) for pi in insumos_existentes}

    return render(
        request,
        "gestion/editar_producto.html",
        {
            "producto_form": producto_form,
            "producto": producto,
            "insumos": insumos,
            "insumos_json": insumos_dict,
        },
    )


def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == "POST":
        producto.delete()
        messages.success(request, "Producto eliminado correctamente.")
        return redirect("listar_productos")
    return render(request, "gestion/eliminar_producto.html", {"producto": producto})


def obtener_productos(request):
    try:
        productos = list(Producto.objects.values("id", "nombre"))
        return JsonResponse({"productos": productos})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def agregar_pedido(request):
    if request.method == "POST":
        print("POST recibido:", request.POST)  # Depuración

        data = request.POST.copy()
        if "estado" not in data or not data["estado"]:
            data["estado"] = "NUEVO"  # Estado por defecto

        form = PedidoForm(data)

        if form.is_valid():
            pedido = form.save()
            print(f"Pedido creado con ID: {pedido.id}")

            producto_ids = request.POST.getlist("producto")
            cantidades = request.POST.getlist("cantidad")

            if not producto_ids or not cantidades:
                messages.error(
                    request, "Debe seleccionar al menos un producto y cantidad."
                )
                return render(
                    request,
                    "gestion/agregar_pedido.html",
                    {"form": form, "productos": Producto.objects.all()},
                )

            productos_creados = []
            stock_insuficiente = []

            for producto_id, cantidad in zip(producto_ids, cantidades):
                if producto_id and cantidad and int(cantidad) > 0:
                    try:
                        producto = Producto.objects.get(id=producto_id)
                        PedidoProducto.objects.create(
                            pedido=pedido, producto=producto, cantidad=int(cantidad)
                        )
                        productos_creados.append(producto)

                        # Verificar stock
                        for prod_insumo in producto.productoinsumo_set.all():
                            insumo = prod_insumo.insumo
                            cantidad_necesaria = prod_insumo.cantidad * int(cantidad)
                            if insumo.stock < cantidad_necesaria:
                                stock_insuficiente.append(
                                    f"{insumo.nombre} (Faltan {cantidad_necesaria - insumo.stock})"
                                )

                    except Producto.DoesNotExist:
                        messages.error(
                            request, f"Producto con ID {producto_id} no encontrado."
                        )
                        return render(
                            request,
                            "gestion/agregar_pedido.html",
                            {"form": form, "productos": Producto.objects.all()},
                        )

            if productos_creados:
                pedido.calcular_totales()
                if stock_insuficiente:
                    messages.warning(
                        request,
                        "Pedido guardado, pero hay stock insuficiente para: "
                        + ", ".join(stock_insuficiente),
                    )
                else:
                    messages.success(request, "Pedido agregado correctamente.")
                return redirect("listar_pedidos")
            else:
                pedido.delete()  # Si no hay productos válidos, eliminar pedido
                messages.error(request, "No se pudieron agregar productos al pedido.")
                return redirect("listar_pedidos")

        else:
            print("Errores del formulario:", form.errors)
            messages.error(
                request, "Error en el formulario. Revisa los datos ingresados."
            )

    else:
        form = PedidoForm()

    return render(
        request,
        "gestion/agregar_pedido.html",
        {"form": form, "productos": Producto.objects.all()},
    )


def editar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    # ❌ Solo se puede editar si está en PRODUCCION
    if pedido.estado != "PRODUCCION":
        messages.warning(request, "Solo se pueden editar pedidos en estado PRODUCCIÓN.")
        return redirect("listar_pedidos")

    if request.method == "POST":
        print("POST recibido para editar:", request.POST)
        form = PedidoForm(request.POST, instance=pedido)

        if form.is_valid():
            form.save()

            # ✅ No permitir agregar nuevos productos, solo modificar cantidades o eliminar
            producto_ids = request.POST.getlist("producto")
            cantidades = request.POST.getlist("cantidad")

            if not producto_ids or not cantidades:
                messages.error(request, "Debe haber al menos un producto con cantidad mayor a 0.")
                return render(request, "gestion/editar_pedido.html", {
                    "form": form, 
                    "pedido": pedido, 
                    "pedido_productos": pedido.pedidoproducto_set.all(), 
                    "productos": Producto.objects.all(),
                })

            productos_actualizados = []
            for ped_prod in pedido.pedidoproducto_set.all():
                if str(ped_prod.producto.id) in producto_ids:
                    index = producto_ids.index(str(ped_prod.producto.id))
                    nueva_cantidad = int(cantidades[index])

                    if nueva_cantidad > 0:
                        ped_prod.cantidad = nueva_cantidad
                        ped_prod.save()
                        productos_actualizados.append(ped_prod.producto)
                    else:
                        # ✅ Si la cantidad es 0, eliminar el producto del pedido
                        ped_prod.delete()

            if productos_actualizados:
                pedido.calcular_totales()
                messages.success(request, "Pedido actualizado correctamente.")
                return redirect("listar_pedidos")
            else:
                # ✅ Si no quedan productos, marcar como CANCELADO
                pedido.estado = "CANCELADO"
                pedido.save()
                messages.warning(request, "El pedido ha sido cancelado porque no tiene productos.")
                return redirect("listar_pedidos")

        else:
            print("Errores del formulario:", form.errors)
            messages.error(request, "Error en el formulario. Revisa los datos ingresados.")

    else:
        form = PedidoForm(instance=pedido)

    return render(
        request,
        "gestion/editar_pedido.html",
        {
            "form": form,
            "pedido": pedido,
            "pedido_productos": pedido.pedidoproducto_set.all(),
            "productos": Producto.objects.all(),
            "estado_actual": pedido.estado,
        },
    )



def eliminar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    if request.method == "POST":
        pedido.delete()
        messages.success(request, "Pedido eliminado correctamente.")
        return redirect("listar_pedidos")
    return render(request, "gestion/eliminar_pedido.html", {"pedido": pedido})


def listar_pedidos(request):
    mostrar_entregados = request.GET.get("mostrar_entregados") == "on"
    mostrar_antiguos = request.GET.get("mostrar_antiguos") == "on"

    fecha_limite = now() - timedelta(days=90)
    fecha_limite_antiguos = now() - timedelta(days=365)

    estados_base = ["NUEVO", "PRODUCCION", "TERMINADO"]
    if mostrar_entregados:
        estados_base += ["ENTREGADO", "CANCELADO"]

    pedidos = Pedido.objects.filter(estado__in=estados_base, fecha__gte=fecha_limite if not mostrar_antiguos else fecha_limite_antiguos).order_by("fecha")

    return render(request, "gestion/listar_pedidos.html", {
        "pedidos": pedidos, "mostrar_entregados": mostrar_entregados, "mostrar_antiguos": mostrar_antiguos
    })


def pagos_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    pagos = pedido.pagos.all()

    if request.method == "POST":
        form = PagoPedidoForm(request.POST)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.pedido = pedido
            pago.save()
            messages.success(request, "Pago agregado correctamente.")
            return JsonResponse({"status": "success"})
        return JsonResponse({"status": "error", "errors": form.errors})

    return render(request, "gestion/pagos_pedido.html", {"pedido": pedido, "pagos": pagos, "pago_form": PagoPedidoForm()})

def eliminar_pago(request, pago_id):
    pago = get_object_or_404(PagoPedido, id=pago_id)
    pago.delete()
    messages.success(request, "Pago eliminado correctamente.")
    return JsonResponse({"status": "success"})

def generar_pdf_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle(f"Pedido_{pedido.id}.pdf")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, 750, f"Pedido #{pedido.id}")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 730, f"Cliente: {pedido.cliente_nombre}")
    pdf.drawString(50, 710, f"Teléfono: {pedido.cliente_telefono}")
    pdf.drawString(50, 690, f"Fecha: {pedido.fecha.strftime('%d/%m/%Y')}")

    pdf.drawString(50, 660, "Productos:")

    y = 640
    for ped_prod in pedido.pedidoproducto_set.all():
        pdf.drawString(70, y, f"- {ped_prod.producto.nombre} (x{ped_prod.cantidad})")
        y -= 20

    pdf.drawString(50, y - 10, f"Total a pagar: ${pedido.total_cobrado}")

    pdf.save()
    buffer.seek(0)

    return FileResponse(buffer, as_attachment=True, filename=f"Pedido_{pedido.id}.pdf")

def cambiar_estado_pedido(request, pedido_id, nuevo_estado):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    # 🚫 No permitir cambios si el pedido está CANCELADO
    if pedido.estado == "CANCELADO":
        return JsonResponse({"error": "No se puede revertir un pedido CANCELADO."}, status=400)

    estado_anterior = pedido.estado

    # 🚫 No permitir cambios desde ENTREGADO excepto a TERMINADO
    if estado_anterior == "ENTREGADO" and nuevo_estado != "TERMINADO":
        return JsonResponse({"error": "Solo se puede volver a TERMINADO desde ENTREGADO."}, status=400)

    pedido.estado = nuevo_estado
    pedido.save()

    # ✅ Si pasa de TERMINADO → PRODUCCIÓN, devolver stock
    if estado_anterior == "TERMINADO" and nuevo_estado == "PRODUCCION":
        for ped_prod in pedido.pedidoproducto_set.all():
            for prod_insumo in ped_prod.producto.productoinsumo_set.all():
                insumo = prod_insumo.insumo
                cantidad_devuelta = prod_insumo.cantidad * ped_prod.cantidad
                insumo.stock += cantidad_devuelta
                insumo.save()
        messages.info(request, "Stock devuelto al cambiar el estado a PRODUCCIÓN.")

    # ✅ Si pasa de PRODUCCIÓN → TERMINADO o PRODUCCIÓN → ENTREGADO, descontar stock
    elif estado_anterior == "PRODUCCION" and nuevo_estado in ["TERMINADO", "ENTREGADO"]:
        stock_insuficiente = []
        for ped_prod in pedido.pedidoproducto_set.all():
            for prod_insumo in ped_prod.producto.productoinsumo_set.all():
                insumo = prod_insumo.insumo
                cantidad_necesaria = prod_insumo.cantidad * ped_prod.cantidad

                if insumo.stock < cantidad_necesaria:
                    stock_insuficiente.append(
                        f"{insumo.nombre} (Faltan {cantidad_necesaria - insumo.stock})"
                    )
                    insumo.stock = 0  # Evitar negativos
                else:
                    insumo.stock -= cantidad_necesaria
                insumo.save()

        if stock_insuficiente:
            messages.error(request, "Stock insuficiente para: " + ", ".join(stock_insuficiente))

    messages.success(request, "Estado del pedido actualizado correctamente.")
    return redirect("listar_pedidos")


@csrf_exempt
def actualizar_ajuste(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == "POST":
        ajuste = request.POST.get("ajuste", "").strip()
        print("Ajuste recibido:", ajuste)

        if ajuste == "":
            ajuste_decimal = Decimal("0")
        else:
            try:
                ajuste_decimal = Decimal(ajuste.replace(",", "."))
            except (ValueError, InvalidOperation):
                return JsonResponse({"error": "Valor de ajuste no válido"}, status=400)

        print("Ajuste decimal guardado:", ajuste_decimal)

        pedido.ajuste = ajuste_decimal
        pedido.save()

        return JsonResponse({
            "mensaje": "Ajuste actualizado correctamente",
            "ajuste": str(pedido.ajuste),
            "total_a_pagar": float(pedido.calcular_total_a_pagar()),
            "restante": float(pedido.calcular_restante())
        })

    return JsonResponse({"error": "Método no permitido"}, status=405)






def informe_ingresos(request):
    hoy = datetime.today()
    hace_6_meses = hoy - timedelta(days=180)

    ingresos_por_mes = (
        Pedido.objects.filter(fecha__gte=hace_6_meses)
        .values("fecha__month")
        .annotate(
            total_ventas=Sum("total_cobrado"),
            total_costos=Sum("total_costo"),
        )
    )

    # 🔹 Convertir número de mes a nombre
    for ingreso in ingresos_por_mes:
        mes_numero = ingreso["fecha__month"]
        ingreso["mes_nombre"] = calendar.month_name[mes_numero]  # 📌 Convierte el número en nombre
        ingreso["ganancia"] = (ingreso["total_ventas"] or 0) - (ingreso["total_costos"] or 0)

    return render(
        request,
        "informes/ingresos.html",
        {"ingresos_por_mes": ingresos_por_mes},
    )

# ✅ INFORMES
def informe_stock_valorizado(request):
    insumos = Insumo.objects.exclude(nombre__iexact="Tiempo de Produccion").exclude(stock=0)

    for insumo in insumos:
        insumo.valor_total = insumo.stock * insumo.costo_unitario

    total_valorizado = sum(insumo.valor_total for insumo in insumos)

    return render(request, "informes/stock_valorizado.html", {
        "insumos": insumos, "total_valorizado": total_valorizado,
    })

def informe_ventas(request):
    fecha_inicio = request.GET.get("fecha_inicio", "")
    fecha_fin = request.GET.get("fecha_fin", "")
    pedidos = Pedido.objects.all()

    if fecha_inicio and fecha_fin:
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1)
        pedidos = pedidos.filter(fecha__date__range=(fecha_inicio.date(), fecha_fin.date()))

    total_por_estado = pedidos.values("estado").annotate(total=Sum("total_cobrado"))

    return render(request, "informes/ventas.html", {
        "pedidos": pedidos, "total_por_estado": total_por_estado,
        "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d") if fecha_inicio else "",
        "fecha_fin": fecha_fin.strftime("%Y-%m-%d") if fecha_fin else "",
    })


def debug_pedidos(request):
    pedidos = Pedido.objects.order_by('-fecha')[:10]
    pedido_id = request.GET.get("pedido_id")

    pedido_seleccionado = None
    productos = []
    pagos = []
    total_pagado = 0
    restante = 0
    modelos = {}

    if pedido_id:
        pedido_seleccionado = get_object_or_404(Pedido, id=pedido_id)
        productos = PedidoProducto.objects.filter(pedido=pedido_seleccionado)
        pagos = PagoPedido.objects.filter(pedido=pedido_seleccionado)
        total_pagado = pagos.aggregate(total=Sum("valor"))["total"] or 0
        restante = pedido_seleccionado.total_cobrado - total_pagado

        def serializar_objeto(obj):
            """ Convierte objetos Django en un diccionario con valores legibles """
            return {
                field.name: getattr(obj, field.name)
                if not isinstance(getattr(obj, field.name), (datetime, Decimal))
                else str(getattr(obj, field.name))  # Convertir datetime y Decimal
                for field in obj._meta.fields
            }

        # Serializar datos de forma dinámica
        modelos["Pedido"] = serializar_objeto(pedido_seleccionado)
        modelos["Productos"] = [serializar_objeto(p) for p in productos]
        modelos["Pagos"] = [serializar_objeto(p) for p in pagos]

    return render(request, "gestion/debug_pedidos.html", {
        "pedidos": pedidos,
        "pedido_seleccionado": pedido_seleccionado,
        "modelos": modelos,
        "total_pagado": total_pagado,
        "restante": restante
    })


def gestionar_pagos(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == "POST":
        valor = request.POST.get("valor")
        banco = request.POST.get("banco")

        if not valor or not banco:
            return JsonResponse({"error": "Debe ingresar un valor y banco válidos."}, status=400)

        try:
            PagoPedido.objects.create(pedido=pedido, valor=float(valor), banco=banco)
            pedido.save()
            return redirect("gestionar_pagos", pedido_id=pedido.id)
        except ValueError:
            return JsonResponse({"error": "El valor del pago no es válido."}, status=400)

    total_pagado = pedido.pagos.aggregate(total=Sum("valor"))["total"] or 0
    restante = pedido.total_cobrado - total_pagado

    return render(request, "gestion/gestionar_pagos.html", {
        "pedido": pedido, "total_pagado": total_pagado, "restante": restante, "pagos": pedido.pagos.all(),
    })