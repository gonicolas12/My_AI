"""
Interface desktop web de My_AI

Une fenêtre native (pywebview) affiche l'interface React de frontend/dist,
servie par un serveur local (server.py) qui relaie le moteur : chat
(core/chat_service.py), agents, Relay et scheduler. Le cycle de vie de l'appli
est dans lifecycle.py, le protocole d'événements dans events.py.
"""
