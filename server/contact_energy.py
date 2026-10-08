"""Energy of the experimental model, not an anatomical energy calibration."""
import numpy as np
from arm import INERTIA

def mechanical_energy(cage,hand,velocity,angular_velocity,bond=None,joint_velocity=None):
    velocity=np.asarray(velocity);omega=np.asarray(angular_velocity)
    inertia=hand.rotation@np.linalg.inv(hand.inverse_inertia)@hand.rotation.T
    edge_error=np.linalg.norm(cage.p[cage.ei]-cage.p[cage.ej],axis=1)-cage.el
    q=cage.p[cage.ti];a,b,c,d=[q[:,i] for i in range(4)]
    volume_error=np.sum((b-a)*np.cross(c-a,d-a),axis=1)/6-cage.tv
    values={'hand_translation':float(.5*velocity@velocity/hand.inverse_mass),
            'hand_rotation':float(.5*omega@inertia@omega),
            'tissue_kinetic':float(.5*np.sum(cage.node_masses[:,None]*cage.v*cage.v)),
            'tissue_edges':float(.5*np.sum(edge_error**2)/cage.edge_compliance),
            'tissue_volumes':float(.5*np.sum(volume_error**2)/cage.volume_compliance),
            'arm_kinetic':float(.5*np.sum(np.asarray(INERTIA)*np.asarray(joint_velocity)**2)) if joint_velocity is not None else 0.,
            'attachment':float(.5*np.sum(bond.error()**2/bond.compliance)) if bond is not None else 0.}
    values['total']=sum(values.values())
    return values
