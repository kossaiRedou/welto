from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required

from .models import User, UserProfile, AppSetting
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm, UserProfileForm,
    UserSearchForm, PasswordChangeForm, AppSettingForm
)


def setup_required(view_func):
    """Décorateur pour vérifier si la configuration initiale est nécessaire"""
    def wrapper(request, *args, **kwargs):
        # Vérifier s'il y a des utilisateurs dans la base
        if not User.objects.exists():
            return redirect('users:setup')
        return view_func(request, *args, **kwargs)
    return wrapper


def setup_view(request):
    """Configuration initiale - Création du premier manager"""
    # Si des utilisateurs existent déjà, rediriger vers la page de login
    if User.objects.exists():
        return redirect('users:login')
    
    if request.method == 'POST':
        # Créer un formulaire de création d'utilisateur
        form_data = request.POST.copy()
        form_data['role'] = 'manager'  # Forcer le rôle manager
        
        form = CustomUserCreationForm(form_data)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'manager'
            user.is_staff = True
            user.is_superuser = True
            user.save()
            
            # Connecter automatiquement l'utilisateur
            login(request, user)
            
            messages.success(
                request, 
                f'Configuration terminée ! Bienvenue {user.get_full_name()}. '
                'Votre compte manager a été créé avec succès.'
            )
            
            return redirect('create-order')
    else:
        form = CustomUserCreationForm()
        # Pré-remplir avec des valeurs par défaut
        form.fields['role'].initial = 'manager'
        form.fields['role'].widget.attrs['readonly'] = True
        form.fields['role'].widget.attrs['disabled'] = True
    
    return render(request, 'users/setup.html', {'form': form})


def login_view(request):
    """Vue de connexion personnalisée"""
    if request.user.is_authenticated:
        return redirect('create-order')
    
    # Vérifier si la configuration initiale est nécessaire
    if not User.objects.exists():
        return redirect('users:setup')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    next_url = request.GET.get('next', 'create-order')
                    
                    # Vérifier que l'URL de redirection est valide
                    if next_url and next_url.startswith('/admin/'):
                        # Si c'est l'admin, rediriger vers la page d'accueil
                        next_url = 'create-order'
                    
                    return redirect(next_url)
                else:
                    messages.error(request, 'Votre compte est désactivé.')
            else:
                messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
        else:
            messages.error(request, 'Veuillez saisir votre nom d\'utilisateur et mot de passe.')
    
    return render(request, 'users/login.html')


def logout_view(request):
    """Vue de déconnexion"""
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('users:login')


def manager_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est manager"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if not request.user.is_manager():
            messages.error(request, 'Accès refusé. Vous devez être manager.')
            return redirect('create-order')
        return view_func(request, *args, **kwargs)
    return wrapper


def employee_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est au moins employé"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def dashboard_view(request):
    """Dashboard principal pour la gestion des utilisateurs"""
    if not request.user.is_manager():
        messages.error(request, 'Accès refusé. Vous devez être manager.')
        return redirect('create-order')
    
    # Statistiques
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    managers = User.objects.filter(role='manager').count()
    employees = User.objects.filter(role='employee').count()
    
    # Utilisateurs récents
    recent_users = User.objects.order_by('-created_at')[:5]
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'managers': managers,
        'employees': employees,
        'recent_users': recent_users,
    }
    
    return render(request, 'users/dashboard.html', context)


@login_required
def app_settings_view(request):
    """Paramètres globaux (devise, seuil de stock) - accessible au manager"""
    if not request.user.is_manager():
        messages.error(request, 'Accès refusé. Vous devez être manager.')
        return redirect('create-order')

    settings_obj = AppSetting.get_solo()
    if request.method == 'POST':
        form = AppSettingForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Paramètres enregistrés avec succès.')
            return redirect('users:app_settings')
    else:
        form = AppSettingForm(instance=settings_obj)

    return render(request, 'users/app_settings.html', {'form': form, 'title': 'Paramètres de l\'application'})


@login_required
def user_list_view(request):
    """Liste des utilisateurs avec filtres"""
    if not request.user.is_manager():
        messages.error(request, 'Accès refusé. Vous devez être manager.')
        return redirect('create-order')
    
    # Formulaire de recherche
    search_form = UserSearchForm(request.GET)
    
    # Filtrage des utilisateurs
    users = User.objects.all()
    
    if search_form.is_valid():
        search = search_form.cleaned_data.get('search')
        role = search_form.cleaned_data.get('role')
        is_active = search_form.cleaned_data.get('is_active')
        
        if search:
            users = users.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(username__icontains=search)
            )
        
        if role:
            users = users.filter(role=role)
        
        if is_active:
            users = users.filter(is_active=is_active == 'True')
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_users': users.count(),
    }
    
    return render(request, 'users/user_list.html', context)


@login_required
def user_create_view(request):
    """Création d'un nouvel utilisateur"""
    if not request.user.is_manager():
        messages.error(request, 'Accès refusé. Vous devez être manager.')
        return redirect('create-order')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request_user=request.user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Utilisateur "{user.get_full_name()}" créé avec succès.')
            return redirect('users:user_list')
        else:
            # Afficher les erreurs de validation
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Erreur {field}: {error}')
    else:
        form = CustomUserCreationForm(request_user=request.user)
    
    context = {
        'form': form,
        'title': 'Créer un nouvel utilisateur',
        'is_create': True,  # Indicateur pour le template
    }
    
    return render(request, 'users/user_form.html', context)


@login_required
def user_update_view(request, pk):
    """Modification d'un utilisateur"""
    if not request.user.is_manager():
        messages.error(request, 'Accès refusé. Vous devez être manager.')
        return redirect('create-order')
    
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user, request_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Utilisateur "{user.get_full_name()}" modifié avec succès.')
            return redirect('users:user_list')
        else:
            # Afficher les erreurs de validation
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Erreur {field}: {error}')
    else:
        form = CustomUserChangeForm(instance=user, request_user=request.user)
    
    context = {
        'form': form,
        'user': user,
        'title': f'Modifier {user.get_full_name()}',
        'is_create': False,  # Indicateur pour le template
    }
    
    return render(request, 'users/user_form.html', context)


@login_required
def user_delete_view(request, pk):
    """Suppression d'un utilisateur"""
    if not request.user.is_manager():
        messages.error(request, 'Accès refusé. Vous devez être manager.')
        return redirect('create-order')
    
    user = get_object_or_404(User, pk=pk)
    
    # Empêcher la suppression de son propre compte
    if user == request.user:
        messages.error(request, 'Vous ne pouvez pas supprimer votre propre compte.')
        return redirect('users:user_list')
    
    if request.method == 'POST':
        user.delete()
        messages.success(request, f'Utilisateur "{user.get_full_name()}" supprimé avec succès.')
        return redirect('users:user_list')
    
    context = {
        'user': user,
        'title': f'Supprimer {user.get_full_name()}',
    }
    
    return render(request, 'users/user_confirm_delete.html', context)


@login_required
def user_profile_view(request, pk):
    """Profil détaillé d'un utilisateur"""
    if not request.user.is_manager():
        messages.error(request, 'Accès refusé. Vous devez être manager.')
        return redirect('create-order')
    
    user = get_object_or_404(User, pk=pk)
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f'Profil de "{user.get_full_name()}" mis à jour.')
            return redirect('users:user_profile', pk=pk)
    else:
        form = UserProfileForm(instance=profile)
    
    context = {
        'user': user,
        'profile': profile,
        'form': form,
        'title': f'Profil de {user.get_full_name()}',
    }
    
    return render(request, 'users/user_profile.html', context)


@login_required
def change_password_view(request, pk):
    """Changement de mot de passe"""
    user = get_object_or_404(User, pk=pk)
    
    # Vérifier les permissions
    if not request.user.is_manager() and request.user != user:
        messages.error(request, 'Accès refusé.')
        return redirect('create-order')
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password1']
            
            # Vérifier le mot de passe actuel
            if not check_password(current_password, user.password):
                messages.error(request, 'Mot de passe actuel incorrect.')
            else:
                # Changer le mot de passe
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Mot de passe modifié avec succès.')
                return redirect('users:user_list')
    else:
        form = PasswordChangeForm()
    
    context = {
        'form': form,
        'user': user,
        'title': f'Changer le mot de passe de {user.get_full_name()}',
    }
    
    return render(request, 'users/change_password.html', context)


@login_required
def my_profile_view(request):
    """Profil de l'utilisateur connecté"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre profil a été mis à jour.')
            return redirect('users:my_profile')
    else:
        form = UserProfileForm(instance=profile)
    
    context = {
        'form': form,
        'title': 'Mon Profil',
    }
    
    return render(request, 'users/my_profile.html', context)


@login_required
def my_password_change_view(request):
    """Changement de mot de passe pour l'utilisateur connecté"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password1']
            
            # Vérifier le mot de passe actuel
            if not check_password(current_password, request.user.password):
                messages.error(request, 'Mot de passe actuel incorrect.')
            else:
                # Changer le mot de passe
                request.user.set_password(new_password)
                request.user.save()
                messages.success(request, 'Mot de passe modifié avec succès.')
                return redirect('users:my_profile')
    else:
        form = PasswordChangeForm()
    
    context = {
        'form': form,
        'title': 'Changer mon mot de passe',
    }
    
    return render(request, 'users/change_password.html', context)


# Vues AJAX pour la gestion dynamique
@login_required
def ajax_user_status_toggle(request, pk):
    """Activer/désactiver un utilisateur via AJAX"""
    if not request.user.is_manager():
        return JsonResponse({'success': False, 'error': 'Accès refusé'})
    
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, pk=pk)
            
            # Empêcher la désactivation de son propre compte
            if user == request.user:
                return JsonResponse({
                    'success': False, 
                    'error': 'Vous ne pouvez pas désactiver votre propre compte'
                })
            
            user.is_active = not user.is_active
            user.save()
            
            return JsonResponse({
                'success': True,
                'is_active': user.is_active,
                'message': f'Compte {"activé" if user.is_active else "désactivé"} avec succès'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@login_required
def ajax_user_search(request):
    """Recherche d'utilisateurs via AJAX"""
    if not request.user.is_manager():
        return JsonResponse({'success': False, 'error': 'Accès refusé'})
    
    if request.method == 'GET':
        search = request.GET.get('search', '').strip()
        
        if len(search) < 2:
            return JsonResponse({'success': True, 'users': []})
        
        users = User.objects.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(username__icontains=search)
        )[:10]
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'name': user.get_full_name(),
                'email': user.email,
                'role': user.get_role_display(),
                'is_active': user.is_active
            })
        
        return JsonResponse({'success': True, 'users': users_data})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
