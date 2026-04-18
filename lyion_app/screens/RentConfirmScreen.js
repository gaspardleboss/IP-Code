// =============================================================================
// RentConfirmScreen.js — Confirms which slot will unlock; calls /api/rent.
// =============================================================================

import React, { useState } from "react";
import {
  View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert,
} from "react-native";
import { requestRent } from "../services/api";

export default function RentConfirmScreen({ route, navigation }) {
  const { slot, stationId } = route.params;
  const [loading, setLoading] = useState(false);

  async function handleConfirm() {
    setLoading(true);
    try {
      const result = await requestRent(stationId);
      Alert.alert(
        "Emplacement déverrouillé !",
        `L'emplacement ${result.slot} s'ouvre. Retirez votre batterie. Charge : ${result.battery_charge ?? "?"}%`,
        [{ text: "OK", onPress: () => navigation.navigate("Rental") }],
      );
    } catch (err) {
      Alert.alert("Erreur", err.message || "Impossible de lancer la location.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Confirmer la location</Text>

      <View style={styles.card}>
        <Text style={styles.slotNumber}>Emplacement {slot.slot_id}</Text>
        <Text style={styles.detail}>Charge : {slot.charge_level ?? "?"}%</Text>
        <Text style={styles.detail}>Station : {stationId}</Text>
      </View>

      <Text style={styles.notice}>
        Un dépôt de garantie sera retenu sur votre compte jusqu'au retour de la batterie.
      </Text>

      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleConfirm}
        disabled={loading}
        accessibilityRole="button"
        accessibilityLabel="Confirmer la location"
      >
        {loading
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.buttonText}>Confirmer et déverrouiller</Text>
        }
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.cancelButton}
        onPress={() => navigation.goBack()}
        disabled={loading}
      >
        <Text style={styles.cancelText}>Annuler</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container:      { flex: 1, backgroundColor: "#F2F2F7", padding: 24, justifyContent: "center" },
  title:          { fontSize: 24, fontWeight: "700", color: "#003DA5", textAlign: "center", marginBottom: 32 },
  card:           { backgroundColor: "#fff", borderRadius: 16, padding: 24, marginBottom: 24,
                    shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 8, elevation: 3 },
  slotNumber:     { fontSize: 36, fontWeight: "800", color: "#003DA5", textAlign: "center" },
  detail:         { fontSize: 16, color: "#3C3C43", textAlign: "center", marginTop: 8 },
  notice:         { fontSize: 13, color: "#8E8E93", textAlign: "center", marginBottom: 32 },
  button:         { backgroundColor: "#003DA5", borderRadius: 14, height: 52,
                    alignItems: "center", justifyContent: "center", marginBottom: 12 },
  buttonDisabled: { opacity: 0.6 },
  buttonText:     { color: "#fff", fontSize: 17, fontWeight: "600" },
  cancelButton:   { alignItems: "center", padding: 12 },
  cancelText:     { color: "#FF3B30", fontSize: 16 },
});
