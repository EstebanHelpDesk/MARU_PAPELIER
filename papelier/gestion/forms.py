from django import forms
from .models import Insumo, Producto, Pedido, ProductoInsumo
from .models import PagoPedido

class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = ['nombre', 'cantidad_total', 'precio_total', 'stock']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'cantidad_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'margen_ganancia']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'margen_ganancia': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['cliente_nombre', 'cliente_telefono', 'cliente_email', 'cliente_instagram', 'estado']
        widgets = {
            'cliente_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'cliente_telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'cliente_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cliente_instagram': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }


class ProductoInsumoForm(forms.ModelForm):
    class Meta:
        model = ProductoInsumo
        fields = ['insumo', 'cantidad']
        widgets = {
            'insumo': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
        }




class PagoPedidoForm(forms.ModelForm):
    class Meta:
        model = PagoPedido
        fields = ["valor", "banco"]
        widgets = {
            "valor": forms.NumberInput(attrs={"class": "form-control"}),
            "banco": forms.TextInput(attrs={"class": "form-control"}),
        }
