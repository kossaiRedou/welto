from django.contrib import admin
from .models import Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('tag_final_price', 'total_price')
    fields = ('product', 'qty', 'price', 'discount_price', 'tag_final_price', 'total_price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'client', 'is_paid', 'tag_final_value', 'timestamp')
    list_filter = ('is_paid', 'date', 'timestamp')
    search_fields = ('title', 'client__name', 'client__phone')
    readonly_fields = ('timestamp', 'tag_final_value', 'value', 'final_value')
    date_hierarchy = 'date'
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('title', 'date', 'client')
        }),
        ('Paiement', {
            'fields': ('is_paid', 'discount', 'value', 'final_value', 'tag_final_value')
        }),
        ('Métadonnées', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        })
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'qty', 'tag_final_price', 'total_price')
    list_filter = ('order__date', 'product__category')
    search_fields = ('order__title', 'product__title')
    readonly_fields = ('tag_final_price', 'tag_price', 'tag_discount', 'final_price', 'total_price')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'date', 'method')
    list_filter = ('method', 'date')
    search_fields = ('order__title',)
    date_hierarchy = 'date'
