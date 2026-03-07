#include "crow_all.h"
#include <fstream>
#include <sstream>
#include <iostream>

// Funcție pentru citirea sigură a fișierelor JSON
std::string read_file(std::string filename) {
    std::ifstream t(filename);
    if (!t.is_open()) return "[]"; // Returnează array gol dacă fișierul nu există încă
    std::stringstream buffer;
    buffer << t.rdbuf();
    return buffer.str();
}

int main() {
    crow::SimpleApp app;

    // RUTA LIVE INTEL (Știri & Hartă)
    CROW_ROUTE(app, "/api/all")
    ([](const crow::request& req, crow::response& res) {
        res.set_header("Access-Control-Allow-Origin", "*");
        res.set_header("Content-Type", "application/json");
        res.write(read_file("intel_data.json"));
        res.end();
    });

    // RUTA EQUIPMENT (Acum din fișier extern)
    CROW_ROUTE(app, "/api/equipment")
    ([](const crow::request& req, crow::response& res) {
        res.set_header("Access-Control-Allow-Origin", "*");
        res.set_header("Content-Type", "application/json");
        res.write(read_file("equipment.json"));
        res.end();
    });

    // RUTA CASUALTIES (Acum din fișier extern)
    CROW_ROUTE(app, "/api/casualties")
    ([](const crow::request& req, crow::response& res) {
        res.set_header("Access-Control-Allow-Origin", "*");
        res.set_header("Content-Type", "application/json");
        res.write(read_file("casualties.json"));
        res.end();
    });

    std::cout << "--- STRATCOM Tactical Server ---" << std::endl;
    std::cout << "[INFO] Terminal online pe portul 18080" << std::endl;
    std::cout << "[INFO] CORS: Enabled pentru conexiuni externe" << std::endl;
    
    app.port(18080).multithreaded().run();
}