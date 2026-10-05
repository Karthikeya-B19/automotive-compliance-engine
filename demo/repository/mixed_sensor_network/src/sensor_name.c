#include "../include/sensor.h"
#include <string.h>

int copy_sensor_name(char *destination, const char *source)
{
    strcpy(destination, source);
    return 0;
}
