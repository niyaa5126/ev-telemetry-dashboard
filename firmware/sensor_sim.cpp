#include <iostream>
#include <iomanip>
#include <cstdint>

struct CANFrame {
    uint32_t id;
    uint8_t dlc;
    uint8_t data[8];
};

CANFrame encode_battery_metrics(float voltage, float current) {
    CANFrame frame;
    frame.id = 0x301;
    frame.dlc = 4;
    uint16_t v_encoded = static_cast<uint16_t>(voltage * 100);
    int16_t  i_encoded = static_cast<int16_t>(current * 10);
    frame.data[0] = (v_encoded >> 8) & 0xFF;
    frame.data[1] = v_encoded & 0xFF;
    frame.data[2] = (i_encoded >> 8) & 0xFF;
    frame.data[3] = i_encoded & 0xFF;
    return frame;
}

CANFrame encode_safety_metrics(float temperature, float soc) {
    CANFrame frame;
    frame.id = 0x302;
    frame.dlc = 3;
    int8_t t_encoded = static_cast<int8_t>(temperature);
    uint16_t soc_encoded = static_cast<uint16_t>(soc * 10);
    frame.data[0] = static_cast<uint8_t>(t_encoded);
    frame.data[1] = (soc_encoded >> 8) & 0xFF;
    frame.data[2] = soc_encoded & 0xFF;
    return frame;
}

int main() {
    return 0;
}
