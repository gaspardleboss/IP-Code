// =============================================================================
// LoginScreen.js — Student login with student number + password.
// =============================================================================

import React, { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  Image, Alert, ActivityIndicator, KeyboardAvoidingView, Platform,
} from "react-native";
import { login } from "../services/api";
import { saveTokens, saveStudent } from "../services/auth";

export default function LoginScreen({ navigation }) {
  const [studentNumber, setStudentNumber] = useState("");
  const [password,      setPassword]      = useState("");
  const [loading,       setLoading]       = useState(false);

  async function handleLogin() {
    if (!studentNumber.trim() || !password) {
      Alert.alert("Champs manquants", "Veuillez entrer votre numéro étudiant et votre mot de passe.");
      return;
    }
    setLoading(true);
    try {
      const data = await login(studentNumber.trim(), password);
      await saveTokens(data.access_token, data.refresh_token);
      await saveStudent(data.student);
      // Navigate to main app — reset stack so user can't go back to login
      navigation.reset({ index: 0, routes: [{ name: "Main" }] });
    } catch (err) {
      Alert.alert("Erreur de connexion", err.message || "Identifiants incorrects.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      {/* Logo placeholder */}
      <View style={styles.logoContainer}>
        <View style={styles.logoPlaceholder}>
          <Text style={styles.logoText}>🔋</Text>
        </View>
        <Text style={styles.brandName}>Ly-ion</Text>
        <Text style={styles.brandTagline}>Powered by Ly-ion</Text>
      </View>

      <Text style={styles.instructions}>
        Connectez-vous avec vos identifiants étudiants
      </Text>

      <TextInput
        style={styles.input}
        placeholder="Numéro étudiant"
        placeholderTextColor="#8E8E93"
        value={studentNumber}
        onChangeText={setStudentNumber}
        autoCapitalize="none"
        keyboardType="default"
        returnKeyType="next"
        accessibilityLabel="Numéro étudiant"
      />

      <TextInput
        style={styles.input}
        placeholder="Mot de passe"
        placeholderTextColor="#8E8E93"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        returnKeyType="done"
        onSubmitEditing={handleLogin}
        accessibilityLabel="Mot de passe"
      />

      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleLogin}
        disabled={loading}
        accessibilityRole="button"
        accessibilityLabel="Se connecter"
      >
        {loading
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.buttonText}>Connexion</Text>
        }
      </TouchableOpacity>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F2F2F7",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 32,
  },
  logoContainer: {
    alignItems: "center",
    marginBottom: 40,
  },
  logoPlaceholder: {
    width: 96,
    height: 96,
    borderRadius: 24,
    backgroundColor: "#003DA5",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  logoText:    { fontSize: 48 },
  brandName:   { fontSize: 32, fontWeight: "700", color: "#003DA5" },
  brandTagline: { fontSize: 13, color: "#8E8E93", marginTop: 4 },
  instructions: {
    fontSize: 15,
    color: "#3C3C43",
    textAlign: "center",
    marginBottom: 28,
  },
  input: {
    width: "100%",
    height: 48,
    backgroundColor: "#fff",
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 16,
    color: "#000",
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#E5E5EA",
  },
  button: {
    width: "100%",
    height: 52,
    backgroundColor: "#003DA5",
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText:     { color: "#fff", fontSize: 17, fontWeight: "600" },
});
