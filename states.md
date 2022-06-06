
## User states

The FeudalAdapter manages local accounts by defining user **states**, as well as only allowing certain **actions** on users, depending on the state they are in.

The user state of the local account is stored and handled by the backend (similar to the mapping: user's OIDC unique ID -> local account).

The currently supported states and their meaning are described in the table below. When implementing a new backend plugin, some states **must** be supported, while others are optional.

| State        | Backend Support | Description |
|--------------|-----------------|-------------|
| deployed     | mandatory       | local account exists and is ready to be used |
| not_deployed | mandatory       | local account does not exist |
| pending      | optional        | creation of local account was requested and is pending approval by site admin (approval workflow) |
| rejected     | optional        | request for creation of local account was rejected by site admin (approval workflow) |
| suspended    | optional        | local account is suspended and cannot be used momentarily;<br>this can happen when the user is no longer authorised to use the service for various reasons (misbehaviour, left the VO, VO no longer authorised) |
| limited      | optional        | user is no longer authorised to use the service (e.g. they left the home organisation or the VO), but they might still be granted limited access to the service (e.g. read-only) for a limited time |
| undefined    | mandatory       | local account is in an undefined state due to an error;<br>please contact support |


## Actions on users

The table below describes all the possible actions that can be performed on local accounts.

There are three possible actors allowed to perform actions:
- the user themselves
- an external administrator (e.g. a VO manager, security staff in the federation)
- a local administrator for the local accounts.

The table also states which actors *should* be allowed to initiate each action, but verifying these roles is not in the scope of the FeudalAdapter, but left to the application that will use the FeudalAdapter.

Such an example is [motley_cue](https://github.com/dianagudu/motley_cue), a REST API that performs authentication, as well as authorisation for users or external admins.
The user and external admin perform their actions via the Motley_Cue API, which triggers actions on the FeudalAdapter.
The site admin can perform actions via the FeudalAdapter interface, or the local user management system.


| Action   | Backend Support | Who can initiate it              | Description |
|----------|-----------------|----------------------------------|-------------|
| deploy   | mandatory       | user                             | triggers the provisioning of a local account, or updates it if local account already exists |
| undeploy | mandatory       | site admin                       | deprovisions a local account |
| accept   | optional        | site admin                       | accepts a pending deployment request from a user;<br>triggers the local account provisioning |
| reject   | optional        | site admin                       | rejects a pending deployment request;<br>a local account is not deployed |
| suspend  | optional        | user, external admin, site admin | suspends a local account;<br>users can suspend their own account if they suspect compromise |
| resume   | optional        | external admin, site admin       | restores a suspended local account |
| limit    | optional        | site admin                       | takes a local account into a “limited” state with limited capabilities |
| unlimit  | optional        | site admin                       | restores a limited local account to full access |


## State transitions

For a clearer picture of how the user states and action are related to each other, the following table depicts all the allowed state transitions: each table cell contains an action that can trigger a transition from an initial state (given by the row) to a final state (given by the column). Impossible / forbidden state transitions are depicted through a dash (-), while a star (*) suggests that all possible actions on a given row can lead to an undefined state.

The three possible actors allowed to perform actions are depicted by different symbols:

```
■ (square)   = user
▲ (triangle) = external admin (VO admin / security)
◆ (diamond)  = site admin
```

| from \ to        | deployed                | not_deployed            | rejected                | pending                 | suspended               | limited                 | undefined |
|-----------------:|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|:---------:|
| **deployed**     | ■ deploy                | ◆ undeploy              | <p align="center">-</p> | <p align="center">-</p> | ■▲◆ suspend             | ◆ limit                 | *         |
| **not_deployed** | ■ deploy                | <p align="center">-</p> | <p align="center">-</p> | ■ deploy                | <p align="center">-</p> | <p align="center">-</p> | *         |
| **pending**      | ◆ accept                | ◆ undeploy              | ◆ reject                | <p align="center">-</p> | <p align="center">-</p> | <p align="center">-</p> | *         |
| **rejected**     | <p align="center">-</p> | ◆ undeploy              | <p align="center">-</p> | <p align="center">-</p> | <p align="center">-</p> | <p align="center">-</p> | *         |
| **suspended**    | ▲ resume                | ◆ undeploy              | <p align="center">-</p> | <p align="center">-</p> | <p align="center">-</p> | ▲ resume                | *         |
| **limited**      | ◆ unlimit               | ◆ undeploy              | <p align="center">-</p> | <p align="center">-</p> | ■▲◆ suspend             | <p align="center">-</p> | *         |
| **undefined**    | <p align="center">-</p> | ◆ undeploy              | <p align="center">-</p> | <p align="center">-</p> | <p align="center">-</p> | <p align="center">-</p> | *         |

