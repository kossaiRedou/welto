from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.db.models import Q
from django.http import JsonResponse
from .models import Product, Category
from .forms import SimpleProductForm, SimpleCategoryForm, QuickStockForm


@staff_member_required
def product_management_home(request):
    """Page d'accueil de la gestion des produits"""
    # Statistiques rapides
    total_products = Product.objects.filter(active=True).count()
    low_stock = Product.objects.filter(active=True, qty__lt=5).count()
    out_of_stock = Product.objects.filter(active=True, qty=0).count()
    categories_count = Category.objects.count()
    
    # Produits récents
    recent_products = Product.objects.filter(active=True).order_by('-id')[:5]
    
    # Produits en stock faible
    low_stock_products = Product.objects.filter(active=True, qty__lt=5, qty__gt=0)[:10]
    
    # Produits en rupture
    out_of_stock_products = Product.objects.filter(active=True, qty=0)[:10]
    
    context = {
        'total_products': total_products,
        'low_stock_count': low_stock,
        'out_of_stock_count': out_of_stock,
        'categories_count': categories_count,
        'recent_products': recent_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
    }
    
    return render(request, 'product/management_home.html', context)


@staff_member_required
def product_list(request):
    """Liste des produits avec recherche et filtres"""
    products = Product.objects.all().order_by('-id')
    
    # Recherche
    search = request.GET.get('search', '')
    if search:
        products = products.filter(
            Q(title__icontains=search) |
            Q(category__title__icontains=search)
        )
    
    # Filtre par catégorie
    category_id = request.GET.get('category', '')
    if category_id:
        products = products.filter(category_id=category_id)
    

    
    # Filtre par statut
    status = request.GET.get('status', '')
    if status == 'active':
        products = products.filter(active=True)
    elif status == 'inactive':
        products = products.filter(active=False)
    
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'search': search,
        'selected_category': category_id,
        'status': status,
    }
    
    return render(request, 'product/product_list.html', context)


@staff_member_required
def add_product(request):
    """Ajouter un nouveau produit"""
    if request.method == 'POST':
        form = SimpleProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Produit "{product.title}" ajouté avec succès!')
            return redirect('product:product_list')
    else:
        form = SimpleProductForm()
    
    return render(request, 'product/add_product.html', {'form': form})


@staff_member_required
def edit_product(request, pk):
    """Modifier un produit"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = SimpleProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Produit "{product.title}" modifié avec succès!')
            return redirect('product:product_list')
    else:
        form = SimpleProductForm(instance=product)
    
    return render(request, 'product/edit_product.html', {'form': form, 'product': product})


@staff_member_required
def delete_product(request, pk):
    """Supprimer un produit"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product_name = product.title
        product.delete()
        messages.success(request, f'Produit "{product_name}" supprimé avec succès!')
        return redirect('product:product_list')
    
    return render(request, 'product/delete_product.html', {'product': product})


@staff_member_required
def quick_stock_update(request, pk):
    """Mise à jour rapide du stock"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = QuickStockForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            quantity = form.cleaned_data['quantity']
            
            if action == 'add':
                product.qty += quantity
                messages.success(request, f'{quantity} unités ajoutées au stock de "{product.title}"')
            elif action == 'remove':
                if product.qty >= quantity:
                    product.qty -= quantity
                    messages.success(request, f'{quantity} unités retirées du stock de "{product.title}"')
                else:
                    messages.error(request, f'Stock insuffisant! Stock actuel: {product.qty}')
                    return redirect('product:product_list')
            elif action == 'set':
                product.qty = quantity
                messages.success(request, f'Stock de "{product.title}" défini à {quantity} unités')
            
            product.save()
            return redirect('product:product_list')
    else:
        form = QuickStockForm()
    
    return render(request, 'product/quick_stock.html', {'form': form, 'product': product})


@staff_member_required
def toggle_product_status(request, pk):
    """Activer/désactiver un produit"""
    product = get_object_or_404(Product, pk=pk)
    product.active = not product.active
    product.save()
    
    status = "activé" if product.active else "désactivé"
    messages.success(request, f'Produit "{product.title}" {status}!')
    
    return redirect('product:product_list')


@staff_member_required
def category_management(request):
    """Gestion des catégories"""
    categories = Category.objects.all().order_by('title')
    
    if request.method == 'POST':
        form = SimpleCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Catégorie "{category.title}" créée avec succès!')
            return redirect('product:category_management')
    else:
        form = SimpleCategoryForm()
    
    context = {
        'categories': categories,
        'form': form,
    }
    
    return render(request, 'product/category_management.html', context)


@staff_member_required
def delete_category(request, pk):
    """Supprimer une catégorie"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        category_name = category.title
        category.delete()
        messages.success(request, f'Catégorie "{category_name}" supprimée avec succès!')
        return redirect('product:category_management')
    
    return render(request, 'product/delete_category.html', {'category': category})


@staff_member_required
def ajax_product_search(request):
    """Recherche AJAX pour les produits"""
    query = request.GET.get('q', '')
    products = Product.objects.filter(
        Q(title__icontains=query) | Q(category__title__icontains=query),
        active=True
    )[:10]
    
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'title': product.title,
            'category': product.category.title if product.category else 'Sans catégorie',
            'price': float(product.final_value),
            'stock': product.qty,
        })
    
    return JsonResponse({'products': results})