// =============================================================================
// SlotCard.js — Individual slot card in the 4×6 station grid.
// =============================================================================

import React from "react";
import { TouchableOpacity, Text, StyleSheet, View } from "react-native";

// Map led_state from backend to display colour and rentability
const LED_CONFIG = {
  BLUE:  { bg: "#0055FF", text: "#fff",  rentable: true  },
  WHITE: { bg: "#E5E5EA", text: "#3C3C43", rentable: false },
  RED:   { bg: "#FF3B30", text: "#fff",  rentable: false },
  GREEN: { bg: "#34C759", text: "#fff",  rentable: false },
  OFF:   { bg: "#2C2C2E", text: "#8E8E93", rentable: false },
};

export default function SlotCard({ slot, onPress }) {
  const cfg = LED_CONFIG[slot.led_state] || LED_CONFIG.OFF;

  return (
    <TouchableOpacity
      style={[styles.card, { backgroundColor: cfg.bg }]}
      onPress={() => onPress(slot)}
      activeOpacity={cfg.rentable ? 0.7 : 0.9}
      accessibilityRole="button"
      accessibilityLabel={`Emplacement ${slot.slot_id}, ${slot.led_state}`}
    >
      <Text style={[styles.number, { color: cfg.text }]}>{slot.slot_id}</Text>
      {slot.charge_level > 0 && (
        <Text style={[styles.charge, { color: cfg.text }]}>{slot.charge_level}%</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    width: "22%",
    aspectRatio: 1,
    borderRadius: 12,
    margin: "1.5%",
    alignItems: "center",
    justifyContent: "center",
  },
  number: { fontSize: 16, fontWeight: "700" },
  charge: { fontSize: 10, marginTop: 2 },
});
