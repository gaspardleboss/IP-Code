// =============================================================================
// SlotGrid.js — 4×6 grid of 24 SlotCard components.
// =============================================================================

import React from "react";
import { View, StyleSheet } from "react-native";
import SlotCard from "./SlotCard";

export default function SlotGrid({ slots, onSlotPress }) {
  // Sort by slot_id so the grid always renders in order 1-24
  const sorted = [...slots].sort((a, b) => a.slot_id - b.slot_id);

  return (
    <View style={styles.grid}>
      {sorted.map((slot) => (
        <SlotCard key={slot.slot_id} slot={slot} onPress={onSlotPress} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  grid: {
    flexDirection: "row",
    flexWrap:      "wrap",
    paddingHorizontal: 8,
    paddingVertical:   8,
  },
});
