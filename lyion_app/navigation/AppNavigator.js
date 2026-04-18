// =============================================================================
// AppNavigator.js — Root navigation: stack + bottom tab navigator.
// =============================================================================

import React, { useState, useEffect } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";

import LoginScreen       from "../screens/LoginScreen";
import QRScanScreen      from "../screens/QRScanScreen";
import StationScreen     from "../screens/StationScreen";
import RentConfirmScreen from "../screens/RentConfirmScreen";
import ActiveRentalScreen from "../screens/ActiveRentalScreen";
import ProfileScreen     from "../screens/ProfileScreen";

import { isLoggedIn } from "../services/auth";

const Stack = createNativeStackNavigator();
const Tab   = createBottomTabNavigator();

// ---------------------------------------------------------------------------
// Bottom tab navigator (shown when logged in)
// ---------------------------------------------------------------------------
function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ color, size }) => {
          const icons = {
            Scan:    "qr-code-outline",
            Rental:  "battery-charging-outline",
            Profile: "person-outline",
          };
          return <Ionicons name={icons[route.name] || "ellipse"} size={size} color={color} />;
        },
        tabBarActiveTintColor:   "#003DA5",
        tabBarInactiveTintColor: "#8E8E93",
        headerShown: false,
      })}
    >
      <Tab.Screen name="Scan"    component={QRScanScreen}       options={{ title: "Scanner" }} />
      <Tab.Screen name="Rental"  component={ActiveRentalScreen} options={{ title: "Location" }} />
      <Tab.Screen name="Profile" component={ProfileScreen}      options={{ title: "Profil" }} />
    </Tab.Navigator>
  );
}

// ---------------------------------------------------------------------------
// Root navigator — handles auth state
// ---------------------------------------------------------------------------
export default function AppNavigator() {
  const [loggedIn, setLoggedIn] = useState(null);

  useEffect(() => {
    isLoggedIn().then(setLoggedIn);
  }, []);

  if (loggedIn === null) return null;   // Splash while checking storage

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {loggedIn ? (
          <>
            <Stack.Screen name="Main"        component={MainTabs} />
            <Stack.Screen name="Station"     component={StationScreen}
                          options={{ headerShown: true, title: "Station" }} />
            <Stack.Screen name="RentConfirm" component={RentConfirmScreen}
                          options={{ headerShown: true, title: "Confirmer la location" }} />
          </>
        ) : (
          <Stack.Screen name="Login" component={LoginScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
