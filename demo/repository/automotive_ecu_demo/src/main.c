#include "../include/vehicle_state.h"

int main(void)
{
    VehicleState state = {0U, 1U};
    update_vehicle_state(&state, "diagnostic-message");
    return 0;
}
