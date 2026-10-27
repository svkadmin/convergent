def phase: if .name == "svc" then 2 elif .name == "wan" then 3
    elif (.name == "fw1" or .name == "fw2") then 4 else 1 end;
. as $now | all($before[0][] | select(.name | test("^(def|int|remmina|tmp-98|svc|wan|fw1|fw2)$"));
    . as $old | [$now[] | select(.name == $old.name)] as $found |
    if (phase) < $stage then
        if $old.ephemeral then ($found | length) == 0
        else ($found | length) == 1 and $found[0].status == "Stopped" and
            all(["boot.autorestart", "user.convergent.autorestart"][];
                . as $key | $found[0].config[$key] == $old.config[$key]) end
    elif (phase) > $stage then ($found | length) == 1 and $found[0].status == "Running"
    else true end)
