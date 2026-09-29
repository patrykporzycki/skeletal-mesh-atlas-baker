#bind layer normal  fpreal3
#bind layer src_tangentu fpreal3
#bind layer src_tangentv fpreal3
#bind layer N fpreal3
#bind layer tangentu fpreal3
#bind layer tangentv fpreal3
#bind layer !&outNormal fpreal3

@KERNEL
{
    fpreal3 n_ts = @normal * 2.0f - 1.0f;
    n_ts.y *= -1.0f;

    fpreal3 T_s = normalize(@src_tangentu);
    fpreal3 N_s = normalize(@N);
    fpreal3 B_s = normalize(@src_tangentv);
    fpreal3 n_w = n_ts.x * T_s + n_ts.y * B_s + n_ts.z * N_s;

    fpreal3 T_d = normalize(@tangentu);
    fpreal3 N_d = normalize(@N);
    fpreal3 B_d = normalize(@tangentv);

    fpreal3 n_d = (fpreal3)(dot(n_w, T_d), dot(n_w, B_d), dot(n_w, N_d));
    @outNormal.set(normalize(n_d) * 0.5f + 0.5f);
}





