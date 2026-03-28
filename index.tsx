import React, { useEffect, useState } from "react";
import { 
  View, 
  Text, 
  TouchableOpacity, 
  FlatList, 
  StyleSheet, 
  Alert, 
  ScrollView, 
  ActivityIndicator 
} from "react-native";
import io, { Socket } from "socket.io-client";

interface LogEntry {
  event: string;
  pin: string;
  timestamp: string;
}

interface UserStat {
  username: string;
  success_count: number;
}

const serverUrl = "http://172.24.20.164:5000"; // ip address
const API_KEY = "ultraelectromagneticpop"; // api key

export default function HomeScreen() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [stats, setStats] = useState<UserStat[]>([]);
  const [unknownCount, setUnknownCount] = useState(0);
  const [loading, setLoading] = useState(true);

// Function to refresh all data 
  const fetchData = async () => {
    try {
      const res = await fetch(`${serverUrl}/history-json`);
      const data = await res.json();
      
      // Update state with new data from server
      setLogs(data.logs || []);
      if (data.user_stats) setStats(data.user_stats);
      if (data.unknown_count !== undefined) setUnknownCount(data.unknown_count);
    } catch (err) {
      console.error("Live update fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    
    fetchData();

    // Setup Socket.IO for live updates
    const socket: Socket = io(serverUrl);

    socket.on("connect", () => {
      console.log("Connected to live update stream");
    });

    // kung ang listener.py sends a log to app.py, app.py emits 'new_log'
    socket.on("new_log", () => {
      console.log("New activity detected! Refreshing...");
      fetchData(); //live update 
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  const openDoor = async () => {
    try {
      const res = await fetch(`${serverUrl}/open-door`, {
        method: "POST",
        headers: { "X-API-KEY": API_KEY },
      });
      const data = await res.json();
      if (res.ok) {
        Alert.alert("Door Status", "Door Unlocked!");
      } else {
        Alert.alert("Error", "Action failed");
      }
    } catch (err: any) {
      Alert.alert("Connection Error", err.message);
    }
  };

  const renderItem = ({ item }: { item: LogEntry }) => {
    const isSuccess = item.event.includes("SUCCESS");
    return (
      <View style={[styles.row, isSuccess ? styles.successRow : styles.failureRow]}>
        <Text style={[styles.cell, isSuccess ? styles.successText : styles.failureText]}>
          {item.event}
        </Text>
        <Text style={styles.cellPin}>{item.pin}</Text>
        <Text style={styles.cellTime}>{item.timestamp}</Text>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Access Dashboard</Text>

      {/* Stats Cards Section - Matches history.html layout */}
      <View style={{ height: 110, marginBottom: 15 }}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.statsContainer}>
          {stats.map((stat, i) => (
            <View key={i} style={styles.statCard}>
              <Text style={styles.statLabel}>{stat.username}</Text>
              <Text style={styles.statValue}>{stat.success_count} Successes</Text>
            </View>
          ))}
          <View style={[styles.statCard, styles.alertCard]}>
            <Text style={styles.statLabel}>Security Alerts</Text>
            <Text style={styles.statValue}>{unknownCount} Unknown PINs</Text>
          </View>
        </ScrollView>
      </View>

      {/* Controls Section */}
      <View style={styles.controls}>
        <TouchableOpacity style={styles.btnOpen} onPress={openDoor}>
          <Text style={styles.btnText}>Open Door</Text>
        </TouchableOpacity>
      </View>

      {/* Table Header */}
      <View style={styles.tableHeader}>
        <Text style={styles.headerText}>Event</Text>
        <Text style={styles.headerText}>PIN</Text>
        <Text style={styles.headerText}>Timestamp</Text>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#1a73e8" />
      ) : (
        <FlatList
          data={logs}
          keyExtractor={(_, index) => index.toString()}
          renderItem={renderItem}
          contentContainerStyle={{ paddingBottom: 20 }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f0f2f5", paddingHorizontal: 15, paddingTop: 50 },
  title: { fontSize: 26, fontWeight: "bold", textAlign: "center", marginBottom: 20, color: "#1a73e8" },
  
 
  statsContainer: { gap: 12, paddingRight: 20 },
  statCard: {
    backgroundColor: "#e3f2fd",
    padding: 15,
    borderRadius: 8,
    borderLeftWidth: 5,
    borderLeftColor: "#2196f3",
    minWidth: 160,
    justifyContent: 'center',
    elevation: 2
  },
  alertCard: { backgroundColor: "#ffebee", borderLeftColor: "#f44336" },
  statLabel: { fontSize: 11, color: "#555", fontWeight: '600', textTransform: 'uppercase' },
  statValue: { fontSize: 15, fontWeight: "bold", color: "#333" },


  controls: { flexDirection: "row", justifyContent: "center", marginBottom: 25 },
  btnOpen: { backgroundColor: "#3498db", paddingVertical: 12, paddingHorizontal: 35, borderRadius: 6, elevation: 3 },
  btnText: { color: "#fff", fontWeight: "600", fontSize: 16 },


  tableHeader: { 
    flexDirection: "row", 
    backgroundColor: "#2c3e50", 
    padding: 15, 
    borderTopLeftRadius: 8, 
    borderTopRightRadius: 8 
  },
  headerText: { flex: 1, color: "#fff", fontWeight: "bold", fontSize: 14 },
  row: { flexDirection: "row", padding: 15, borderBottomWidth: 1, borderBottomColor: "#eee" },
  successRow: { backgroundColor: "#d4edda" },
  failureRow: { backgroundColor: "#f8d7da" },
  successText: { color: "#155724" },
  failureText: { color: "#721c24" },
  cell: { flex: 1, fontSize: 13, fontWeight: '600' },
  cellPin: { flex: 1, fontSize: 14, fontFamily: 'monospace', color: '#333' },
  cellTime: { flex: 1.2, fontSize: 12, color: "#555" },
});