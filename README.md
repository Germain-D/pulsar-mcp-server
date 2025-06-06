# Pulsar MCP Server

Un serveur MCP (Message Context Protocol) pour Apache Pulsar qui permet aux modèles IA d'interagir avec les topics, producteurs et consommateurs Pulsar de manière native.

## 🚀 Fonctionnalités

- **Publication de messages** sur les topics Pulsar
- **Consommation de messages** depuis les topics Pulsar
- **Gestion des topics** (création, suppression, liste)
- **Statistiques détaillées** des topics et souscriptions
- **Authentification JWT/TLS** pour les clusters sécurisés
- **Interface MCP standard** compatible avec Claude Desktop et autres clients MCP

## 📋 Prérequis

- Python 3.8+
- Apache Pulsar en cours d'exécution
- Accès réseau aux services Pulsar (ports 6650 et 8080 par défaut)

## 🛠️ Installation

1. **Cloner le projet** :
```bash
git clone <votre-repo>
cd pulsar-mcp-server
```

2. **Créer un environnement virtuel** :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. **Installer les dépendances** :
```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

Créez un fichier `.env` dans le répertoire racine :

```bash
# Paramètres de connexion Pulsar
PULSAR_SERVICE_URL=pulsar://localhost:6650
PULSAR_WEB_SERVICE_URL=http://localhost:8080

# Configuration des topics et souscriptions
TOPIC_NAME=my-topic
SUBSCRIPTION_NAME=pulsar-mcp-subscription
SUBSCRIPTION_TYPE=Shared
IS_TOPIC_READ_FROM_BEGINNING=False

# Authentification (optionnel)
# PULSAR_TOKEN=eyJhbGciOiJIUzI1NiJ9...
# PULSAR_TLS_TRUST_CERTS_FILE_PATH=/path/to/ca-cert.pem
# PULSAR_TLS_ALLOW_INSECURE_CONNECTION=False

# Descriptions des outils (optionnel)
TOOL_PUBLISH_DESCRIPTION=Publishes information to the configured Pulsar topic
TOOL_CONSUME_DESCRIPTION=Consumes information from the configured Pulsar topic
```

### Types de souscription supportés :
- `Exclusive` : Un seul consommateur
- `Shared` : Partage entre plusieurs consommateurs
- `Failover` : Basculement automatique
- `KeyShared` : Partage basé sur les clés

## 🚀 Utilisation

### Lancement du serveur

**Avec transport stdio** (recommandé pour Claude Desktop) :
```bash
python main.py --transport stdio
```

**Avec transport SSE** (pour développement/debug) :
```bash
python main.py --transport sse --host localhost --port 3001
```

**Options disponibles** :
- `--transport` : stdio ou sse (défaut: stdio)
- `--host` : Hôte pour SSE (défaut: localhost)
- `--port` : Port pour SSE (défaut: 3001)
- `--log-level` : DEBUG, INFO, WARNING, ERROR (défaut: INFO)

## 🛠️ Outils disponibles

### 1. `pulsar-publish`
Publie un message sur un topic Pulsar.

**Paramètres** :
- `topic` (requis) : Nom du topic de destination
- `message` (requis) : Contenu du message
- `properties` (optionnel) : Propriétés du message (clé-valeur)

### 2. `pulsar-consume`
Consomme des messages depuis un topic Pulsar.

**Paramètres** :
- `topic` (requis) : Nom du topic source
- `subscription_name` (optionnel) : Nom de la souscription
- `max_messages` (optionnel) : Nombre max de messages (1-100, défaut: 10)

### 3. `pulsar-create-topic`
Crée un nouveau topic Pulsar.

**Paramètres** :
- `topic` (requis) : Nom du topic à créer
- `partitions` (optionnel) : Nombre de partitions (défaut: 1)

### 4. `pulsar-delete-topic`
Supprime un topic Pulsar existant.

**Paramètres** :
- `topic` (requis) : Nom du topic à supprimer

### 5. `pulsar-list-topics`
Liste tous les topics du cluster Pulsar.

**Paramètres** : Aucun

### 6. `pulsar-topic-stats`
Récupère les statistiques d'un topic.

**Paramètres** :
- `topic` (requis) : Nom du topic

## 📱 Intégration avec Claude Desktop

Ajoutez cette configuration dans votre fichier de configuration Claude Desktop :

```json
{
    "mcpServers": {
        "pulsar": {
            "command": "python",
            "args": [
                "/chemin/vers/votre/projet/main.py"
            ],
            "env": {
                "PULSAR_SERVICE_URL": "pulsar://localhost:6650",
                "PULSAR_WEB_SERVICE_URL": "http://localhost:8080"
            }
        }
    }
}
```

## 🐳 Utilisation avec Docker

### Lancer Pulsar avec Docker
```bash
# Pulsar standalone
docker run -it -p 6650:6650 -p 8080:8080 apachepulsar/pulsar:latest bin/pulsar standalone
```

### Construire l'image du serveur MCP
```bash
# Créer un Dockerfile si nécessaire
cat > Dockerfile << EOF
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py", "--transport", "stdio"]
EOF

# Construire et exécuter
docker build -t pulsar-mcp-server .
docker run -it --network host pulsar-mcp-server
```

## 🔒 Sécurité

### Authentification JWT
```bash
# Dans votre .env
PULSAR_TOKEN=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0LXVzZXIifQ...
```

### TLS/SSL
```bash
# Dans votre .env
PULSAR_SERVICE_URL=pulsar+ssl://pulsar.example.com:6651
PULSAR_TLS_TRUST_CERTS_FILE_PATH=/path/to/ca-cert.pem
PULSAR_TLS_ALLOW_INSECURE_CONNECTION=False
```

## 🐛 Dépannage

### Problèmes de connexion
1. Vérifiez que Pulsar est en cours d'exécution
2. Testez la connectivité : `telnet localhost 6650`
3. Vérifiez les logs : `--log-level DEBUG`

### Erreurs d'authentification
1. Vérifiez la validité du token JWT
2. Confirmez les permissions sur les topics
3. Testez avec `pulsar-admin`

### Problèmes de performance
1. Ajustez `send_timeout_millis` dans `pulsar_connector.py`
2. Modifiez `batching_enabled` selon vos besoins
3. Augmentez `max_messages` pour la consommation

## 📊 Monitoring

Le serveur génère des logs détaillés avec :
- Connexions/déconnexions Pulsar
- Messages publiés/consommés
- Erreurs et exceptions
- Statistiques de performance

Format des logs :
```
2024-01-15 10:30:45 - pulsar_connector - INFO - Connected to Pulsar at pulsar://localhost:6650
2024-01-15 10:30:46 - pulsar_connector - INFO - Message published to topic my-topic with ID: 123:45:0
```

## 🤝 Contribution

1. Fork le projet
2. Créez une branche feature (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est sous licence Apache 2.0. Voir le fichier `LICENSE` pour plus de détails.

## 🔗 Liens utiles

- [Documentation Apache Pulsar](https://pulsar.apache.org/docs/)
- [Spécification MCP](https://modelcontextprotocol.io/)
- [Claude Desktop](https://claude.ai/desktop)
- [Documentation MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) 