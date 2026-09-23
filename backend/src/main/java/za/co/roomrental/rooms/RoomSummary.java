package za.co.roomrental.rooms;

public record RoomSummary(
        String id,
        String name,
        String area,
        String roomType,
        int monthlyRent,
        String details,
        String description,
        String status
) {
}
