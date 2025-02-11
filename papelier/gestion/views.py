from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from .models import Insumo, Producto, Pedido, ProductoInsumo, PedidoProducto, PagoPedido
from .forms import InsumoForm, ProductoForm, PedidoForm
from django.db.models import F, ExpressionWrapper, FloatField
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from django.utils.timezone import now
from datetime import timedelta
from django.http import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from datetime import datetime
from django.db.models import Sum
import calendar

def home(request):
    ultimos_pedidos = Pedido.objects.exclude(estado="ENTREGADO").order_by("-fecha")[:15]
    insumos_bajos = Insumo.objects.annotate(
        threshold=ExpressionWrapper(
            F("cantidad_total") * 0.1, output_field=FloatField()
        )
    ).filter(stock__lt=F("threshold"))
    return render(
        request,
        "gestion/home.html",
        {"ultimos_pedidos": ultimos_pedidos, "insumos_bajos": insumos_bajos},
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

    if request.method == "POST":
        print("POST recibido para editar:", request.POST)
        form = PedidoForm(request.POST, instance=pedido)

        if form.is_valid():
            form.save()

            pedido.pedidoproducto_set.all().delete()  # Eliminar productos existentes

            producto_ids = request.POST.getlist("producto")
            cantidades = request.POST.getlist("cantidad")

            if not producto_ids or not cantidades:
                messages.error(
                    request, "Debe seleccionar al menos un producto y cantidad."
                )
                return render(
                    request,
                    "gestion/editar_pedido.html",
                    {
                        "form": form,
                        "pedido": pedido,
                        "pedido_productos": pedido.pedidoproducto_set.all(),
                        "productos": Producto.objects.all(),
                    },
                )

            productos_actualizados = []
            for producto_id, cantidad in zip(producto_ids, cantidades):
                if producto_id and cantidad and int(cantidad) > 0:
                    try:
                        producto = Producto.objects.get(id=producto_id)
                        PedidoProducto.objects.create(
                            pedido=pedido, producto=producto, cantidad=int(cantidad)
                        )
                        productos_actualizados.append(producto)
                    except Producto.DoesNotExist:
                        messages.error(
                            request, f"Producto con ID {producto_id} no encontrado."
                        )
                        return render(
                            request,
                            "gestion/editar_pedido.html",
                            {
                                "form": form,
                                "pedido": pedido,
                                "pedido_productos": pedido.pedidoproducto_set.all(),
                                "productos": Producto.objects.all(),
                            },
                        )

            if productos_actualizados:
                pedido.calcular_totales()
                messages.success(request, "Pedido actualizado correctamente.")
                return redirect("listar_pedidos")
            else:
                pedido.estado = "CANCELADO"  # Si no hay productos, cancelar pedido
                pedido.save()
                messages.warning(
                    request, "El pedido ha sido cancelado porque no tiene productos."
                )
                return redirect("listar_pedidos")

        else:
            print("Errores del formulario:", form.errors)
            messages.error(
                request, "Error en el formulario. Revisa los datos ingresados."
            )

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


@csrf_exempt
def cambiar_estado_pedido(request, pedido_id, nuevo_estado):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    pedido.estado = nuevo_estado
    pedido.save()

    stock_insuficiente = []

    # Verificar y ajustar stock si el pedido se TERMINA
    if nuevo_estado == "TERMINADO":
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
        messages.error(
            request, "El stock es insuficiente para: " + ", ".join(stock_insuficiente)
        )

    messages.success(request, "Estado del pedido actualizado correctamente.")
    return redirect("listar_pedidos")




def listar_pedidos(request):
    mostrar_entregados = request.GET.get("mostrar_entregados") == "on"
    mostrar_antiguos = request.GET.get("mostrar_antiguos") == "on"

    fecha_limite = now() - timedelta(days=90)
    fecha_limite_antiguos = now() - timedelta(days=365)

    estados_base = ["NUEVO", "PENDIENTE", "EN PRODUCCION", "TERMINADO"]
    if mostrar_entregados:
        estados_base += ["ENTREGADO", "CANCELADO"]

    if mostrar_antiguos:
        pedidos = Pedido.objects.filter(estado__in=estados_base, fecha__gte=fecha_limite_antiguos).order_by("fecha")
    else:
        pedidos = Pedido.objects.filter(estado__in=estados_base, fecha__gte=fecha_limite).order_by("fecha")

    return render(request, "gestion/listar_pedidos.html", {"pedidos": pedidos, "mostrar_entregados": mostrar_entregados, "mostrar_antiguos": mostrar_antiguos})


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



def informe_stock_valorizado(request):
    insumos = Insumo.objects.exclude(nombre__iexact="tiempo de produccion")  # Excluir "tiempo de producción"
    #excluir los que tienen cantidad=0
    insumos = insumos.exclude(stock=0)
    
    # Agregar el cálculo del valor total de cada insumo
    for insumo in insumos:
        insumo.valor_total = insumo.stock * insumo.costo_unitario

    # Calcular el total valorizado
    total_valorizado = sum(insumo.valor_total for insumo in insumos)

    return render(request, "informes/stock_valorizado.html", {
        "insumos": insumos,
        "total_valorizado": total_valorizado,
    })



def informe_ventas(request):
    fecha_inicio = request.GET.get("fecha_inicio", "")
    fecha_fin = request.GET.get("fecha_fin", "")
    pedidos = Pedido.objects.all()

    if fecha_inicio and fecha_fin:
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d")
        #los pedidos tienen fecha y hora y los parametros solo fecha
        #por lo que se debe agregar un dia a la fecha fin para que tome los pedidos del dia, quitar la hora de los pedidos a la hora de realizar el filtro
        pedidos = pedidos.filter(fecha__date__range=(fecha_inicio.date(), fecha_fin.date()))


    # Agrupar por estado y sumar total_cobrado
    total_por_estado = pedidos.values("estado").annotate(total=Sum("total_cobrado"))

    return render(request, "informes/ventas.html", {
        "pedidos": pedidos,
        "total_por_estado": total_por_estado,
        "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d") if fecha_inicio else "",
        "fecha_fin": fecha_fin.strftime("%Y-%m-%d") if fecha_fin else "",
    })


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

    elif request.method == "DELETE":
        try:
            data = json.loads(request.body)
            pago_id = data.get("pago_id")
            pago = get_object_or_404(PagoPedido, id=pago_id, pedido=pedido)
            pago.delete()
            return JsonResponse({"mensaje": "Pago eliminado correctamente."})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Solicitud incorrecta."}, status=400)

    total_pagado = pedido.pagos.aggregate(total=Sum("valor"))["total"] or 0
    restante = pedido.total_cobrado - total_pagado

    return render(
        request,
        "gestion/gestionar_pagos.html",
        {
            "pedido": pedido,
            "total_pagado": total_pagado,
            "restante": restante,
            "pagos": pedido.pagos.all(),
        },
    )