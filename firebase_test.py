import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Тестовий запис
doc_ref = db.collection("test").document("hello")
doc_ref.set({"msg": "Привіт, Firestore!"})

print("✅ Firestore працює!")
