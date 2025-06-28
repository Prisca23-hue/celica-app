
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
    
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('inactif', 'Inactif'),
        ('en_attente', 'En attente'),
        ('suspendu', 'Suspendu'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')
    matricule = models.CharField(max_length=20, unique=True)
    specialite = models.CharField(max_length=100, blank=True)
    niveau = models.CharField(max_length=50, blank=True)
    date_preinscription = models.DateTimeField(auto_now_add=True)
    date_naissance = models.DateField(null=True, blank=True)
    derniere_connexion = models.DateTimeField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Propriétés pour l'accès aux champs du User associé
    @property
    def email(self):
        return self.user.email
    
    @property
    def first_name(self):
        return self.user.first_name
    
    @property
    def last_name(self):
        return self.user.last_name
    
    @property
    def username(self):
        return self.user.username

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def changer_mot_de_passe(self, nouveau_mot_de_passe):
        """Change le mot de passe de l'utilisateur"""
        self.user.set_password(nouveau_mot_de_passe)
        self.user.save()

    def check_password(self, password):
        """Vérifie le mot de passe"""
        return self.user.check_password(password)

    @classmethod
    def rechercher(cls, mot_cle):
        """Recherche des utilisateurs par mot-clé"""
        return cls.objects.filter(
            models.Q(user__username__icontains=mot_cle) |
            models.Q(user__email__icontains=mot_cle) |
            models.Q(user__first_name__icontains=mot_cle) |
            models.Q(user__last_name__icontains=mot_cle) |
            models.Q(matricule__icontains=mot_cle)
        )

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

    def supprimer_module(self):
        """Supprime le module si aucune dépendance active"""
        # Vérifier les cours actifs
        cours_actifs = self.cours_set.filter(status='actif')
        if cours_actifs.exists():
            raise ValueError("Impossible de supprimer un module avec des cours actifs.")
        
        # Vérifier les tests actifs
        tests_actifs = self.test_set.filter(is_active=True)
        if tests_actifs.exists():
            raise ValueError("Impossible de supprimer un module avec des tests actifs.")
        
        self.delete()

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

    @classmethod
    def importer_depuis_pdf(cls, fichier_pdf, module, instructeur):
        """Importe un cours depuis un fichier PDF"""
        import pdfplumber
        
        contenu_extrait = ""
        with pdfplumber.open(fichier_pdf) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    contenu_extrait += text + "\n"
        
        if not contenu_extrait.strip():
            raise ValueError("Le fichier PDF ne contient pas de texte extractible.")
        
        # Créer le cours
        cours = cls.objects.create(
            titre=f"Cours importé - {fichier_pdf.name}",
            description=f"Cours importé depuis le fichier PDF {fichier_pdf.name}",
            contenu=contenu_extrait,
            module=module,
            instructeur=instructeur,
            status='actif'
        )
        
        return cours

    def supprimer(self):
        """Supprime le cours si possible"""
        # Vérifier si des plannings actifs existent
        now = timezone.now()
        plannings_actifs = self.module.planning_set.filter(
            date_debut__lte=now,
            date_fin__gte=now
        )
        if plannings_actifs.exists():
            raise ValueError("Impossible de supprimer un cours lié à des plannings actifs.")
        
        self.delete()

    def exporter(self, format_fichier):
        """Exporte le cours dans le format spécifié"""
        if format_fichier == 'pdf':
            # Logique d'exportation PDF
            pass
        elif format_fichier == 'txt':
            return self.contenu.encode('utf-8')
        else:
            raise ValueError("Format non supporté")

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
    instructeur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.texte[:50]}..." if self.texte else f"{self.enonce[:50]}..."

class ChoixReponse(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choix')
    texte = models.CharField(max_length=500)
    est_correcte = models.BooleanField(default=False)
    explication = models.TextField(blank=True)
    ordre = models.IntegerField(default=1)

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
    randomize_questions = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=[('brouillon', 'Brouillon'), ('publié', 'Publié')], default='brouillon')

    def __str__(self):
        return self.titre

    @classmethod
    def importer_depuis_fichier(cls, fichier, module, format_fichier):
        """Importe un test depuis un fichier"""
        # Logique d'importation selon le format
        pass

    def exporter(self, format_fichier):
        """Exporte le test dans le format spécifié"""
        if format_fichier not in ['csv', 'excel', 'pdf']:
            raise ValueError("Format non supporté")
        # Logique d'exportation
        pass

    def remplacer_question(self, ancienne_question_id, enonce, niveau_difficulte, type_question, reponses):
        """Remplace une question dans le test"""
        ancienne_question = Question.objects.get(id=ancienne_question_id, test=self)
        
        # Créer la nouvelle question
        nouvelle_question = Question.objects.create(
            enonce=enonce,
            type_question=type_question,
            niveau_difficulte=niveau_difficulte,
            module=self.module,
            instructeur=self.instructeur
        )
        
        # Ajouter les réponses
        for reponse_data in reponses:
            Reponse.objects.create(
                question=nouvelle_question,
                texte=reponse_data['texte'],
                est_correcte=reponse_data['est_correcte']
            )
        
        # Remplacer dans le test
        self.questions.remove(ancienne_question)
        self.questions.add(nouvelle_question)
        
        # Supprimer l'ancienne question
        ancienne_question.delete()

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
    date_passation = models.DateTimeField(auto_now_add=True)
    duree_reelle = models.IntegerField()  # en minutes
    reussi = models.BooleanField()

    def __str__(self):
        return f"{self.apprenant.user.username} - {self.test.titre} - {self.note}"

    def calculer_note(self, score):
        """Calcule la note basée sur le score"""
        self.note = (score / 100) * self.test.bareme
        self.save()

    def exporter(self, format_fichier):
        """Exporte le résultat dans le format spécifié"""
        if format_fichier not in ['csv', 'excel', 'pdf']:
            raise ValueError("Format non supporté")
        # Logique d'exportation
        pass

class Groupe(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=20, unique=True, blank=True)
    capacite_max = models.IntegerField(default=50)
    apprenants = models.ManyToManyField(Utilisateur, related_name='groupes_apprenant', blank=True)
    instructeurs = models.ManyToManyField(Utilisateur, related_name='groupes_instructeur', blank=True)
    membres = models.ManyToManyField(Utilisateur, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    actif = models.BooleanField(default=True)

    def __str__(self):
        return self.nom

class Planning(models.Model):
    titre = models.CharField(max_length=200)
    nom = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=[('planifie', 'Planifié'), ('en_cours', 'En cours'), ('termine', 'Terminé')], default='planifie')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, null=True, blank=True)
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE)
    groupes = models.ManyToManyField(Groupe, related_name='plannings', blank=True)
    createur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    instructeur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='plannings_instructeur', null=True, blank=True)
    instructeur_responsable = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='plannings_responsable', null=True, blank=True)
    is_published = models.BooleanField(default=False)
    publie = models.BooleanField(default=False)

    def __str__(self):
        return self.titre

    def exporter(self, format_fichier):
        """Exporte le planning dans le format spécifié"""
        if format_fichier not in ['csv', 'excel', 'pdf']:
            raise ValueError("Format non supporté")
        # Logique d'exportation
        pass

class Notification(models.Model):
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('success', 'Succès'),
        ('error', 'Erreur'),
        ('support', 'Support'),
    ]

    titre = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    type_notice = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    type_notification = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    priorite = models.CharField(max_length=20, choices=[('basse', 'Basse'), ('normale', 'Normale'), ('haute', 'Haute')], default='normale')
    destinataire = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, null=True, blank=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='notifications_recues', null=True, blank=True)
    instructeur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='notifications_envoyees', null=True, blank=True)
    emetteur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='notifications_emises', null=True, blank=True)
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

    def marquer_comme_lue(self):
        """Marque la notification comme lue"""
        self.lu = True
        self.est_lue = True
        self.save()

    @classmethod
    def creer_notification(cls, titre, message, type_notice, utilisateur, module=None, instructeur=None):
        """Crée une nouvelle notification"""
        return cls.objects.create(
            titre=titre,
            message=message,
            type_notice=type_notice,
            utilisateur=utilisateur,
            module=module,
            instructeur=instructeur
        )

class Aide(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    categorie = models.CharField(max_length=100, blank=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    createur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)

    def __str__(self):
        return self.titre

    @classmethod
    def rechercher_aide(cls, mot_cle):
        """Recherche dans les aides par mot-clé"""
        return cls.objects.filter(
            models.Q(titre__icontains=mot_cle) |
            models.Q(contenu__icontains=mot_cle) |
            models.Q(categorie__icontains=mot_cle)
        )

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
    taux_reussite = models.FloatField(help_text='Taux de réussite en pourcentage')
    date = models.DateTimeField(auto_now_add=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, null=True, blank=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.type} - {self.valeur}"

    def generer_rapport(self, format_fichier):
        """Génère un rapport statistique dans le format spécifié"""
        if format_fichier not in ['csv', 'excel', 'pdf']:
            raise ValueError("Format non supporté")
        # Logique de génération de rapport
        pass

# Alias pour compatibilité
Statistiques = Statistique
