
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('insumos/', views.listar_insumos, name='listar_insumos'),
    path('insumos/agregar/', views.agregar_insumo, name='agregar_insumo'),
    path('productos/', views.listar_productos, name='listar_productos'),
    path('pedidos/', views.listar_pedidos, name='listar_pedidos'),
    path('productos/agregar/', views.agregar_producto, name='agregar_producto'),
    path('productos/editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('productos/eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    path('insumos/editar/<int:insumo_id>/', views.editar_insumo, name='editar_insumo'),
    path('insumos/eliminar/<int:insumo_id>/', views.eliminar_insumo, name='eliminar_insumo'),
    path('pedidos/agregar/', views.agregar_pedido, name='agregar_pedido'),
    path('pedidos/editar/<int:pedido_id>/', views.editar_pedido, name='editar_pedido'),
    path('pedidos/cambiar_estado/<int:pedido_id>/<str:nuevo_estado>/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('pedidos/eliminar/<int:pedido_id>/', views.eliminar_pedido, name='eliminar_pedido'),
    path('obtener_productos/', views.obtener_productos, name='obtener_productos'),
    path('pedidos/pdf/<int:pedido_id>/', views.generar_pdf_pedido, name='generar_pdf_pedido'),
    path("informes/stock_valorizado/", views.informe_stock_valorizado, name="informe_stock_valorizado"),
    path("informes/ventas/", views.informe_ventas, name="informe_ventas"),
    path("informes/ingresos/", views.informe_ingresos, name="informe_ingresos"),
    path("pedidos/<int:pedido_id>/pagos/", views.gestionar_pagos, name="gestionar_pagos"),

]
