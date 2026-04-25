import sys
import os
import time

# Set up environment variables to use a local SQLite DB for the demo
os.environ["FLASK_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite:///demo_app.db"

# Add current directory to path so we can import from the backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Student, Station, Slot, Battery, Session
from werkzeug.security import generate_password_hash

def setup_demo_db(app):
    with app.app_context():
        # Insert the user if they don't exist
        email = "g.vancompernolle@ecam.fr"
        password = "123"
        
        student = Student.query.filter_by(email=email).first()
        if not student:
            print(f"[*] Adding user {email} to the database...")
            student = Student(
                student_number="ECAM_001",
                name="Gaspard Vancompernolle",
                email=email,
                password_hash=generate_password_hash(password),
                is_active=True
            )
            db.session.add(student)
            db.session.commit()
            print("[*] User successfully added.")
        else:
            print(f"[*] User {email} already exists in the database.")
            # Update password just in case
            student.password_hash = generate_password_hash(password)
            db.session.commit()
            
        # Add a battery for the demo if there are none
        battery = Battery.query.first()
        if not battery:
            print("[*] Adding a test battery...")
            battery = Battery(battery_uid="BATT-TEST-01", charge_level=100)
            db.session.add(battery)
            db.session.commit()
            
        # Assign battery to a slot
        slot = Slot.query.filter_by(battery_id=None).first()
        if slot and battery:
            slot.battery_id = battery.id
            db.session.commit()

def run_demo(app):
    with app.app_context():
        print("\n" + "="*50)
        print("  LY-ION APP - SIMULATION DE DÉVERROUILLAGE")
        print("="*50 + "\n")
        
        entered_email = input("Identifiant étudiant (Email) : ")
        entered_pass = input("Mot de passe : ")
        
        print("\n[*] Vérification des identifiants...")
        time.sleep(1)
        
        from werkzeug.security import check_password_hash
        student = Student.query.filter_by(email=entered_email).first()
        
        if not student or not check_password_hash(student.password_hash, entered_pass):
            print("[!] Identifiants incorrects. Simulation annulée.")
            return
            
        print(f"[+] Connexion réussie, bienvenue {student.name} !\n")
        time.sleep(1)
        
        print(">>> DEMANDE DE DÉVERROUILLAGE EN COURS...")
        time.sleep(2)
        
        # Trouver une batterie disponible
        slot = Slot.query.filter(Slot.battery_id != None).first()
        if not slot:
            print("[!] Aucune batterie disponible pour le moment.")
            return
            
        print(f"[+] Batterie {slot.battery.battery_uid} déverrouillée au slot {slot.id} !")
        print("\n" + "-"*50)
        print("📢 MESSAGE IMPORTANT :")
        print("-> Vous avez 1h d'utilisation gratuite avant de devoir rendre la batterie.")
        print("-> Vous avez 24h pour rendre la batterie, sinon une caution sera prélevée.")
        print("-"*50 + "\n")
        
        # Create a session to simulate the rental
        new_session = Session(
            student_id=student.id,
            slot_id=slot.id,
            battery_id=slot.battery_id
        )
        db.session.add(new_session)
        # Empty the slot
        slot.battery_id = None
        db.session.commit()
        
        print("[*] Simulation terminée avec succès.")

if __name__ == "__main__":
    app = create_app()
    setup_demo_db(app)
    run_demo(app)
