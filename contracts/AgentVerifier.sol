// contracts/AgentVerifier.sol
// SPDX-License-Identifier: ISC
pragma solidity ^0.8.20;

contract AgentVerifier {
    struct ActionData {
        bytes32 hash;   // canonical hash of (inputs, outputs, ts)
        string cid;     // off-chain JSON with model/data provenance
        uint256 ts;     // unix seconds
    }

    // agent => list of actions (append-only)
    mapping(address => ActionData[]) private actions;

    // --- NEW: points / token ledger ---
    mapping(address => int256) private points;

    // --- NEW: agent registry for discovery in UI ---
    address[] private agents;
    mapping(address => bool) private isKnownAgent;

    // ownership (simple)
    address public owner;
    modifier onlyOwner() { require(msg.sender == owner, "not owner"); _; }

    // events
    event ActionRecorded(address indexed agent, bytes32 hash, string cid, uint256 ts, uint256 indexed actionIndex);
    event ActionEvaluated(address indexed agent, uint256 indexed actionIndex, bool good, uint256 delta, int256 newPoints, string reason);

    constructor() {
        owner = msg.sender;
    }

    // --- existing self-record method (for wallets/agents that call directly) ---
    function recordAction(bytes32 _hash, string memory _cid, uint256 _ts) external {
        _record(msg.sender, _hash, _cid, _ts);
    }

    // --- NEW: server/evaluator can record on behalf of an agent (demo-friendly) ---
    function recordActionFor(address agent, bytes32 _hash, string memory _cid, uint256 _ts) external onlyOwner {
        _record(agent, _hash, _cid, _ts);
    }

    function _record(address agent, bytes32 _hash, string memory _cid, uint256 _ts) internal {
        if (!isKnownAgent[agent]) {
            isKnownAgent[agent] = true;
            agents.push(agent);
        }
        actions[agent].push(ActionData({hash: _hash, cid: _cid, ts: _ts}));
        emit ActionRecorded(agent, _hash, _cid, _ts, actions[agent].length - 1);
    }

    // --- NEW: evaluate an action and adjust points ---
    function evaluateAction(address agent, uint256 index, bool good, uint256 delta, string calldata reason) external onlyOwner {
        require(index < actions[agent].length, "bad index");
        int256 newBal = points[agent] + (good ? int256(delta) : -int256(delta));
        points[agent] = newBal;
        emit ActionEvaluated(agent, index, good, delta, newBal, reason);
    }

    // views
    function getActionCount(address agent) external view returns (uint256) {
        return actions[agent].length;
    }

    function getAction(address agent, uint256 index) external view returns (bytes32, string memory, uint256) {
        ActionData storage a = actions[agent][index];
        return (a.hash, a.cid, a.ts);
    }

    function getAllActions(address agent) external view returns (ActionData[] memory) {
        return actions[agent];
    }

    // --- NEW: points + discovery ---
    function getPoints(address agent) external view returns (int256) {
        return points[agent];
    }

    function listAgents() external view returns (address[] memory) {
        return agents;
    }
}
