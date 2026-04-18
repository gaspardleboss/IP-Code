// =============================================================================
// StationScreen.js — Displays all 24 slots of a station after QR scan.
// Polls backend every 5 seconds for live updates.
// =============================================================================

import React, { useState, useEffect, useCallback } from "react";
import {
  View, Text, StyleSheet, ActivityIndicator, Alert,
  RefreshControl, ScrollView,
} from "react-native";
import { fetchSlots } from "../services/api";
import SlotGrid from "../components/SlotGrid";

const POLL_INTERVAL_MS = 5000;

export default function StationScreen({ route, navigation }) {
  const { stationId } = route.params;
  const [slots,       setSlots]       = useState([]);
  const [stationName, setStationName] = useState("Chargement…");
  const [loading,     setLoading]     = useState(true);
  const [refreshing,  setRefreshing]  = useState(false);
  const [error,       setError]       = useState(null);

  const loadSlots = useCallback(async () => {
    try {
      const data = await fetchSlots(stationId);
      setSlots(data.slots || []);
      setStationName(data.location_name || stationId);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [stationId]);

  // Initial load + polling
  useEffect(() => {
    loadSlots();
    const interval = setInterval(loadSlots, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [loadSlots]);

  function handleSlotPress(slot) {
    if (slot.led_state !== "BLUE") {
      Alert.alert("Emplacement indisponible",
        slot.is_defective
          ? "Cet emplacement est marqué défectueux."
          : "Ce slot n'est pas disponible à la location.");
      return;
    }
    navigation.navigate("RentConfirm", { slot, stationId });
  }

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#003DA5" />
        <Text style={styles.loadingText}>Chargement de la station…</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadSlots(); }} />}
    >
      <Text style={styles.stationName}>{stationName}</Text>

      {error ? (
        <Text style={styles.error}>Erreur : {error}</Text>
      ) : (
        <>
          <SlotGrid slots={slots} onSlotPress={handleSlotPress} />
          <View style={styles.legend}>
            {[
              { color: "#0000FF", label: "Disponible" },
              { color: "#ffffff", label: "En charge",  border: true },
              { color: "#FF0000", label: "Indisponible" },
              { color: "#00FF00", label: "En cours d'utilisation" },
              { color: "#555",    label: "Vide / maintenance" },
            ].map((item) => (
              <View key={item.label} style={styles.legendRow}>
                <View style={[styles.dot, { backgroundColor: item.color },
                              item.border && styles.dotBorder]} />
                <Text style={styles.legendLabel}>{item.label}</Text>
              </View>
            ))}
          </View>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: "#F2F2F7" },
  centered:     { flex: 1, alignItems: "center", justifyContent: "center" },
  loadingText:  { marginTop: 12, color: "#8E8E93", fontSize: 15 },
  stationName:  { fontSize: 20, fontWeight: "700", color: "#003DA5",
                  textAlign: "center", marginVertical: 16 },
  error:        { color: "#FF3B30", textAlign: "center", margin: 20 },
  legend:       { marginHorizontal: 16, marginTop: 8, marginBottom: 32 },
  legendRow:    { flexDirection: "row", alignItems: "center", marginBottom: 6 },
  dot:          { width: 16, height: 16, borderRadius: 8, marginRight: 10 },
  dotBorder:    { borderWidth: 1, borderColor: "#ccc" },
  legendLabel:  { fontSize: 14, color: "#3C3C43" },
});
