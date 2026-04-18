// =============================================================================
// QRScanScreen.js — QR code scanner screen.
// Decodes lyion://station/<token> and navigates to the StationScreen.
// =============================================================================

import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, Alert } from "react-native";
import { Camera } from "expo-camera";
import { BarCodeScanner } from "expo-barcode-scanner";
import { isLoggedIn } from "../services/auth";

export default function QRScanScreen({ navigation }) {
  const [hasPermission, setHasPermission] = useState(null);
  const [scanned,       setScanned]       = useState(false);

  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === "granted");
    })();
  }, []);

  // Re-allow scanning each time the screen comes into focus
  useEffect(() => {
    const unsub = navigation.addListener("focus", () => setScanned(false));
    return unsub;
  }, [navigation]);

  async function handleBarCodeScanned({ type, data }) {
    setScanned(true);

    // Validate deep-link format: lyion://station/<qr_token>
    const match = data.match(/^lyion:\/\/station\/([a-zA-Z0-9_-]+)$/);
    if (!match) {
      Alert.alert("QR Code invalide", "Ce QR code n'appartient pas à une station Ly-ion.", [
        { text: "Réessayer", onPress: () => setScanned(false) },
      ]);
      return;
    }
    const stationToken = match[1];

    // Guard: require login
    const loggedIn = await isLoggedIn();
    if (!loggedIn) {
      Alert.alert(
        "Connexion requise",
        "Connectez-vous à votre compte étudiant pour continuer.",
        [
          { text: "Se connecter", onPress: () => navigation.navigate("Login") },
          { text: "Annuler",      onPress: () => setScanned(false) },
        ],
      );
      return;
    }

    navigation.navigate("Station", { stationId: stationToken });
  }

  if (hasPermission === null)   return <Text style={styles.msg}>Demande d'accès à la caméra…</Text>;
  if (hasPermission === false)  return <Text style={styles.msg}>Accès à la caméra refusé.</Text>;

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Scanner le QR Code de la borne</Text>
      <BarCodeScanner
        onBarCodeScanned={scanned ? undefined : handleBarCodeScanned}
        style={styles.scanner}
        barCodeTypes={[BarCodeScanner.Constants.BarCodeType.qr]}
      />
      {scanned && (
        <Text style={styles.scanning}>Traitement en cours…</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  header:    {
    color: "#fff",
    textAlign: "center",
    fontSize: 16,
    fontWeight: "600",
    paddingVertical: 20,
    backgroundColor: "#003DA5",
  },
  scanner:   { flex: 1 },
  scanning:  { color: "#fff", textAlign: "center", padding: 16, fontSize: 15 },
  msg:       { flex: 1, textAlign: "center", marginTop: 200, fontSize: 16, color: "#333" },
});
