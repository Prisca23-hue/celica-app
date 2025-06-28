from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

class Utilisateur(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('instructeur', 'Instructeur'),
        ('apprenant', 'Apprenant'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    date_creation = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

class Module(models.Model):
    nom = models.CharField(max_length=200)
    intitule = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    categorie = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=[('actif', 'Actif'), ('inactif', 'Inactif')], default='actif')
    instructeur_principal = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='modules_principaux', null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    createur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)

    def __str__(self):
        return self.intitule if self.intitule else self.nom

class Cours(models.Model):
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    contenu = models.TextField()
    status = models.CharField(max_length=20, choices=[('actif', 'Actif'), ('inactif', 'Inactif')], default='actif')
    fichier = models.FileField(upload_to='cours/', blank=True, null=True)
    date_cloture = models.DateTimeField(null=True, blank=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    instructeur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre

class Question(models.Model):
    TYPE_CHOICES = [
        ('qcm', 'QCM'),
        ('vrai_faux', 'Vrai/Faux'),
        ('texte', 'Texte libre'),
        ('QCM', 'QCM'),
        ('QRL', 'QRL'),
    ]

    texte = models.TextField()
    enonce = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    type_question = models.CharField(max_length=20, choices=TYPE_CHOICES, default='QCM')
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    difficulte = models.IntegerField(choices=[(i, i) for i in range(1, 6)], default=1)
    niveau_difficulte = models.CharField(max_length=20, choices=[('facile', 'Facile'), ('moyen', 'Moyen'), ('difficile', 'Difficile')], default='facile')
    points = models.IntegerField(default=1)
    ponderation = models.FloatField(default=1.0)
    explication = models.TextField(blank=True)
    ordre = models.IntegerField(default=0)
    image = models.ImageField(upload_to='questions/', blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.texte[:50]}..." if self.texte else f"{self.enonce[:50]}..."

class ChoixReponse(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choix')
    texte = models.CharField(max_length=500)
    est_correcte = models.BooleanField(default=False)
    explication = models.TextField(blank=True)

    def __str__(self):
        return self.texte

# Alias pour compatibilité avec le code existant
class Reponse(ChoixReponse):
    class Meta:
        proxy = True

class Test(models.Model):
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    questions = models.ManyToManyField(Question, through='TestQuestion')
    duree = models.IntegerField()  # Durée en minutes
    bareme = models.FloatField()   # Barème total
    duree_minutes = models.IntegerField()
    note_passage = models.FloatField()
    date_creation = models.DateTimeField(auto_now_add=True)
    createur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    instructeur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='tests_crees', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.titre

class TestQuestion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    ordre = models.IntegerField()

    class Meta:
        ordering = ['ordre']
        unique_together = ['test', 'question']

class Resultat(models.Model):
    apprenant = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    note = models.FloatField()
    score = models.FloatField()
    appreciation = models.CharField(max_length=20, choices=[('insuffisant', 'Insuffisant'), ('passable', 'Passable'), ('bien', 'Bien'), ('excellent', 'Excellent')], default='passable')
    temps_ecoule = models.IntegerField()  # en minutes
    temps_passe = models.IntegerField(null=True, blank=True)  # en minutes
    commentaires = models.TextField(blank=True)
    date_passage = models.DateTimeField()
    date = models.DateTimeField(auto_now_add=True)
    duree_reelle = models.IntegerField()  # en minutes
    reussi = models.BooleanField()

    def __str__(self):
        return f"{self.apprenant.user.username} - {self.test.titre} - {self.note}"

class Groupe(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    capacite_max = models.IntegerField(default=50)
    apprenants = models.ManyToManyField(Utilisateur, related_name='groupes_apprenant', blank=True)
    membres = models.ManyToManyField(Utilisateur, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

class Planning(models.Model):
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=[('planifie', 'Planifié'), ('en_cours', 'En cours'), ('termine', 'Terminé')], default='planifie')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, null=True, blank=True)
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE)
    createur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)

    def __str__(self):
        return self.titre

class Notification(models.Model):
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('success', 'Succès'),
        ('error', 'Erreur'),
    ]

    titre = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    type_notice = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    priorite = models.CharField(max_length=20, choices=[('basse', 'Basse'), ('normale', 'Normale'), ('haute', 'Haute')], default='normale')
    destinataire = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, null=True, blank=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='notifications_recues', null=True, blank=True)
    instructeur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='notifications_envoyees', null=True, blank=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True)
    test = models.ForeignKey(Test, on_delete=models.CASCADE, null=True, blank=True)
    resultat = models.ForeignKey('Resultat', on_delete=models.CASCADE, null=True, blank=True)
    date_expiration = models.DateTimeField(null=True, blank=True)
    lu = models.BooleanField(default=False)
    est_lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_envoi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre

class Aide(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    categorie = models.CharField(max_length=100, blank=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    createur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)

    def __str__(self):
        return self.titre

class APropos(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    version = models.CharField(max_length=50)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.titre} - v{self.version}"

class Statistique(models.Model):
    TYPE_CHOICES = [
        ('test_completion', 'Completion de test'),
        ('user_activity', 'Activité utilisateur'),
        ('module_progress', 'Progression module'),
    ]

    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    valeur = models.FloatField()
    date = models.DateTimeField(auto_now_add=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, null=True, blank=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.type} - {self.valeur}"