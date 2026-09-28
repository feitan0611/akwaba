---
title: L'assistant Akwaba
source: Documentation du projet (dépôt du projet, docs/ et ADR)
updated: 2026-09-28
author: équipe projet
---
# Qui est Akwaba

Akwaba est un assistant vocal prototype conçu par un groupe de sept apprenants en Côte d'Ivoire. Il permet de poser une question à voix haute dans une langue locale et d'entendre la réponse dans la même langue.

Akwaba est un projet de formation : ses réponses peuvent contenir des erreurs et doivent être vérifiées auprès d'une personne compétente pour toute décision importante.

# Langues prises en charge

Akwaba fonctionne en Dioula : il comprend une question parlée en Dioula et répond en Dioula, à l'écrit et à voix haute.

Le Baoulé est en préparation. Aucun modèle public ne permet encore de reconnaître, traduire ou prononcer le Baoulé ; l'équipe collecte un corpus de Baoulé pour entraîner un modèle.

En interne, Akwaba traduit la question en français, prépare la réponse en français, puis la traduit dans la langue de l'utilisateur.

# Comment lui parler

On peut écrire une question dans la zone de saisie, ou appuyer sur le micro pour envoyer un message vocal.

Le mode conversation vocale, avec l'orbe, permet de parler sans toucher de bouton : l'assistant écoute, répond à voix haute, puis écoute de nouveau. Pour l'arrêter, il suffit de toucher l'orbe ou la croix.

# Confidentialité

Les messages vocaux sont envoyés au serveur pour être traités, puis ils ne sont pas conservés. L'historique des conversations est enregistré uniquement dans le navigateur de l'utilisateur, sous forme de texte, et peut être effacé dans les paramètres.

# Limites

Akwaba ne remplace pas un médecin, un agent de santé ou un service officiel. Pour une urgence, il faut contacter directement les secours ou un centre de santé.

Akwaba ne connaît que les informations de sa base de connaissances et ses connaissances générales. Il ne connaît pas les prix du jour, l'actualité ni les horaires précis des services, sauf s'ils ont été ajoutés à sa base avec une source.
