package za.co.roomrental.rooms;

import java.util.List;
import java.util.Locale;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

@RestController
@RequestMapping("/api/v1/rooms")
@CrossOrigin(origins = {"http://localhost:5173", "http://127.0.0.1:5173"})
public class RoomController {
    private static final List<RoomSummary> DEMO_ROOMS = List.of(
            new RoomSummary("room-obs-ensuite", "Sunny en-suite room", "Observatory, Cape Town", "En-suite", 4200, "Furnished · WiFi · Water", "A bright north-facing room with built-in cupboards, a desk, fibre-ready internet and a private bathroom.", "AVAILABLE"),
            new RoomSummary("room-obs-double", "Garden-facing double room", "Observatory, Cape Town", "Double", 3800, "Furnished · Garden · Parking", "A spacious double room opening onto a quiet garden, with a shared bathroom and kitchen access.", "AVAILABLE"),
            new RoomSummary("room-sandton-studio", "Sandton bachelor studio", "Sandton, Johannesburg", "Studio", 6500, "Furnished · Parking · Water", "A secure bachelor studio close to Gautrain Sandton station, with a kitchenette and balcony.", "AVAILABLE"),
            new RoomSummary("room-sosh-single", "Student single room", "Soshanguve, Pretoria", "Single", 2500, "WiFi · Water · Shared home", "An affordable room near TUT Soshanguve with a communal kitchen, study room and WiFi.", "AVAILABLE")
    );

    @GetMapping
    public List<RoomSummary> search(
            @RequestParam(defaultValue = "") String q,
            @RequestParam(defaultValue = "") String roomType,
            @RequestParam(defaultValue = "0") int minPrice,
            @RequestParam(defaultValue = "0") int maxPrice
    ) {
        String query = q.trim().toLowerCase(Locale.ROOT);
        return DEMO_ROOMS.stream()
                .filter(room -> query.isEmpty() || (room.name() + " " + room.area()).toLowerCase(Locale.ROOT).contains(query))
                .filter(room -> roomType.isBlank() || room.roomType().equalsIgnoreCase(roomType))
                .filter(room -> minPrice <= 0 || room.monthlyRent() >= minPrice)
                .filter(room -> maxPrice <= 0 || room.monthlyRent() <= maxPrice)
                .toList();
    }

        @GetMapping("/{roomId}")
        public RoomSummary detail(@PathVariable String roomId) {
                return DEMO_ROOMS.stream()
                                .filter(room -> room.id().equals(roomId))
                                .findFirst()
                                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Room not found"));
        }
}
