// =============================================================================
// ProfileScreen.js — Student info, deposit balance, logout.
// =============================================================================

import React, { useState, useEffect } from "react";
import {
  View, Text, StyleSheet, TouchableOpacity, Alert, ScrollView,
} from "react-native";
import { getStudent, clearTokens } from "../services/auth";

export default function ProfileScreen({ navigation }) {
  const [student, setStudent] = useState(null);

  useEffect(() => {
    getStudent().then(setStudent);
  }, []);

  function handleLogout() {
    Alert.alert("Déconnexion", "Êtes-vous sûr de vouloir vous déconnecter ?", [
      { text: "Annuler", style: "cancel" },
      {
        text: "Déconnecter",
        style: "destructive",
        onPress: async () => {
          await clearTokens();
          navigation.reset({ index: 0, routes: [{ name: "Login" }] });
        },
      },
    ]);
  }

  if (!student) {
    return (
      <View style={styles.centered}>
        <Text>Chargement du profil…</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Mon Profil</Text>

      <View style={styles.card}>
        <InfoRow label="Nom"              value={student.name} />
        <InfoRow label="N° étudiant"      value={student.student_number} />
        <InfoRow label="Email"            value={student.email || "—"} />
        <InfoRow label="Solde de dépôt"   value={`${student.deposit_balance?.toFixed(2) ?? "0.00"} €`} />
        <InfoRow label="Carte RFID"       value={student.card_uid ? "Enregistrée ✓" : "Non enregistrée"} />
      </View>

      <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
        <Text style={styles.logoutText}>Déconnexion</Text>
      </TouchableOpacity>

      <Text style={styles.footer}>Powered by Ly-ion</Text>
    </ScrollView>
  );
}

function InfoRow({ label, value }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: "#F2F2F7" },
  centered:     { flex: 1, alignItems: "center", justifyContent: "center" },
  title:        { fontSize: 24, fontWeight: "700", color: "#003DA5",
                  textAlign: "center", marginVertical: 24 },
  card:         { backgroundColor: "#fff", borderRadius: 16, marginHorizontal: 16,
                  marginBottom: 24, overflow: "hidden" },
  row:          { flexDirection: "row", justifyContent: "space-between",
                  padding: 16, borderBottomWidth: 1, borderBottomColor: "#F2F2F7" },
  label:        { fontSize: 15, color: "#8E8E93" },
  value:        { fontSize: 15, color: "#1C1C1E", fontWeight: "500", maxWidth: "60%", textAlign: "right" },
  logoutButton: { backgroundColor: "#FF3B30", borderRadius: 14, height: 52, margin: 16,
                  alignItems: "center", justifyContent: "center" },
  logoutText:   { color: "#fff", fontSize: 17, fontWeight: "600" },
  footer:       { textAlign: "center", color: "#C7C7CC", fontSize: 12, marginBottom: 32 },
});
