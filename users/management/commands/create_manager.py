from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

class Command(BaseCommand):
    help = 'Créer le premier utilisateur manager'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Nom d\'utilisateur pour le manager'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@welto.com',
            help='Email pour le manager'
        )
        parser.add_argument(
            '--first-name',
            type=str,
            default='Admin',
            help='Prénom du manager'
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default='Manager',
            help='Nom du manager'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='Mot de passe pour le manager'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        first_name = options['first_name']
        last_name = options['last_name']
        password = options['password']

        try:
            # Vérifier si un utilisateur existe déjà
            if User.objects.exists():
                self.stdout.write(
                    self.style.WARNING(
                        'Des utilisateurs existent déjà dans la base de données. '
                        'Utilisez l\'interface d\'administration pour créer des utilisateurs.'
                    )
                )
                return

            # Créer le premier manager
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                role='manager',
                is_staff=True,
                is_superuser=True
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Manager créé avec succès !\n'
                    f'Nom d\'utilisateur: {username}\n'
                    f'Mot de passe: {password}\n'
                    f'Email: {email}\n'
                    f'Nom complet: {first_name} {last_name}'
                )
            )
            
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  IMPORTANT: Changez le mot de passe après la première connexion !'
                )
            )

        except IntegrityError:
            self.stdout.write(
                self.style.ERROR(
                    f'Erreur: Un utilisateur avec le nom d\'utilisateur "{username}" existe déjà.'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erreur lors de la création du manager: {e}')
            ) 