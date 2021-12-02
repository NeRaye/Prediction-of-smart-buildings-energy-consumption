# Predection of smart buildings energy consumption 

Prédiction de la consommation de gaz et d'électricité d'un bâtiment intelligent, à partir des données de consommation et des données météorologiques. La prédiction se fait selon 4 granularités temporelles (heure, jour, semaine, mois).

1. Tests et résultats:   

  * La visualisation 
  * Le prétraitement 
  * L'implementation de deux approches d'apprentissage supervisé : la régression et la prévision des séries temporelles.
  
  Pour la régression les modèles de régression linéaire multiple, SVM (kernel linéaire, polynomiale et RGB) et les forêts aléatoires ont été implémentés avec la bibliothèque scikit-learn.  Pour la prévision des séries temporelles, le modèle statistique ARIMA a été implémenté avec la bibliothéques statsmodels et le réseau de neurones LSTM avec le framework Keras.
  
  La sélection d'attribut a été faite avec la méthode Sequential feature Sélection (SFS). Les choix des hyperparamètres optimaux été font avec un algorithme de recherche sur grille en se basant sur le résultat de la validation croisée.

 
 2. Déploiment: 
 Le LSTM a était déployé sur une API REST développé avec FLASK. L'interface utilisateur et elle développe avec HTML, CSS et JS, elle permet de visualiser les résultats de la prédiction.
  
  
