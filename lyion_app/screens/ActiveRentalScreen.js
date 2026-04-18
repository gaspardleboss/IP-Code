// =============================================================================
// ActiveRentalScreen.js — Shows ongoing rental and "Return battery" action.
// =============================================================================

import React, { useState, useEffect } from "react";
import {
  View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert,
} from "react-native";
import { getStudent } from "../services/auth";
import { returnBattery } from "../services/api";

export default function ActiveRentalScreen({ navigation }) {
  const [student,   setStudent]   = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [returning, setReturning] = useState(false);

  useEffect(() => {
    getStudent().then(setStudent);
  }, []);

  async function handleReturn() {
    Alert.alert(
      "Retourner la batterie",
      "Assurez-vous que la batterie est bien insérée dans l'emplacement avant de confirmer.",
      [
        { text: "Annuler", style: "cancel" },
        {
          text: "Confirmer le retour",
          onPress: async () => {
            setReturning(true);
            try {
              // For app-initiated returns, the station/slot info should come from
              // the active session stored locally or fetched from backend.
              // Here we prompt the user to scan the QR code for now.
              Alert.alert(
                "Retour confirmé",
                "Insérez la batterie dans un emplacement libre de la borne et tapez votre carte, ou utilisez le bouton de retour dans l'app.",
              );
            } catch (err) {
              Alert.alert("Erreur", err.message);
            } finally {
              setReturning(false);
            }
          },
        },
      ],
    );
  }

  if (!student) {
    return (
      <View style={styles.centered}>
        <Text style={styles.noRental}>Aucune location active.</Text>
        <Text style={styles.hint}>Scannez un QR code sur une borne pour commencer.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Location en cours</Text>

      <View style={styles.card}>
        <Text style={styles.name}>{student.name}</Text>
        <Text style={styles.detail}>N° étudiant : {student.student_number}</Text>
      </View>

      <Text style={styles.instructions}>
        Rendez la batterie à n'importe quelle borne Ly-ion en l'insérant dans
        un emplacement libre, puis tapez votre carte RFID.
      </Text>

      <TouchableOpacity
        style={[styles.returnButton, returning && styles.disabled]}
        onPress={handleReturn}
        disabled={returning}
      >
        {returning
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.returnText}>Retourner la batterie</Text>
        }
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container:     { flex: 1, backgroundColor: "#F2F2F7", padding: 24, justifyContent: "center" },
  centered:      { flex: 1, alignItems: "center", justifyContent: "center", padding: 32 },
  title:         { fontSize: 24, fontWeight: "700", color: "#003DA5", textAlign: "center", marginBottom: 32 },
  card:          { backgroundColor: "#fff", borderRadius: 16, padding: 24, marginBottom: 24,
                   shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 8, elevation: 3 },
  name:          { fontSize: 20, fontWeight: "700", color: "#1C1C1E", textAlign: "center" },
  detail:        { fontSize: 15, color: "#8E8E93", textAlign: "center", marginTop: 6 },
  instructions:  { fontSize: 14, color: "#3C3C43", textAlign: "center", marginBottom: 32, lineHeight: 22 },
  returnButton:  { backgroundColor: "#34C759", borderRadius: 14, height: 52,
                   alignItems: "center", justifyContent: "center" },
  returnText:    { color: "#fff", fontSize: 17, fontWeight: "600" },
  disabled:      { opacity: 0.6 },
  noRental:      { fontSize: 20, fontWeight: "600", color: "#3C3C43", textAlign: "center" },
  hint:          { fontSize: 14, color: "#8E8E93", textAlign: "center", marginTop: 12 },
});
