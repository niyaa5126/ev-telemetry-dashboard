"""
CAN Frame Deserializer & DBC Parser for 16S BMS System.
Simulates unpacking 8-byte payloads from Arbitration IDs 0x401-0x404.
"""

class CANBMSDecoder:
    @staticmethod
    def decode_cell_frame(frame_bytes: bytes, base_cell_idx: int = 1):
        """
        Unpacks an 8-byte CAN frame containing 4 series cell voltages.
        Encoding: 16-bit Big-Endian per cell, 1 mV resolution (0.001 V).
        """
        if len(frame_bytes) != 8:
            raise ValueError("CAN standard frame payload must be exactly 8 bytes.")
        
        cells = {}
        for i in range(4):
            # Extract 2 bytes per cell
            msb = frame_bytes[i * 2]
            lsb = frame_bytes[i * 2 + 1]
            raw_v = (msb << 8) | lsb
            voltage = round(raw_v / 1000.0, 3)
            cells[f"Cell {base_cell_idx + i}"] = voltage
            
        return cells

    @staticmethod
    def parse_hex_string(can_id: str, hex_payload: str):
        """
        Parse raw logged CAN traffic (e.g. ID: 0x401, Data: 0C E4 0C EE 0C D8 0C F0)
        """
        clean_hex = hex_payload.replace(" ", "").strip()
        payload_bytes = bytes.fromhex(clean_hex)
        
        id_map = {
            "0x401": 1,
            "0x402": 5,
            "0x403": 9,
            "0x404": 13
        }
        
        base_idx = id_map.get(can_id.lower(), 1)
        return CANBMSDecoder.decode_cell_frame(payload_bytes, base_cell_idx=base_idx)

if __name__ == "__main__":
    # Test decoding frame 0x401 with raw cell voltages (approx 3.3V each)
    # 3.300V -> 3300 mV -> 0x0CE4
    sample_payload = "0C E4 0C E8 0C EE 0C D5"
    results = CANBMSDecoder.parse_hex_string("0x401", sample_payload)
    print("Decoded 0x401 CAN Frame Cell Telemetry:")
    for cell, v in results.items():
        print(f"  {cell}: {v:.3f} V")
