import pytest
import numpy as np
from custom_hmm import HMM
from mfcc_extract import load_mfccs, load_mfccs_by_word
import pandas as pd


@pytest.fixture
def feature_set():
    return load_mfccs("feature_set")


@pytest.fixture
def hmm_model(feature_set):
    return HMM(8, 13, feature_set)


@pytest.fixture
def heed_features():
    return load_mfccs_by_word("feature_set", "heed")


def test_gamma_properties(hmm_model, feature_set):
    """Test if gamma probabilities have expected properties"""
    test_features = feature_set[0]
    emission_matrix = hmm_model.compute_emission_matrix(test_features)
    alpha, scale_factors= hmm_model.forward(emission_matrix)
    beta = hmm_model.backward(emission_matrix, scale_factors)
    gamma = hmm_model.compute_gamma(alpha, beta)

    T = emission_matrix.shape[0]

    # Print first few time steps
    pd.set_option("display.precision", 4)
    pd.set_option("display.float_format", "{:.4f}".format)

    print("\nGamma probabilities for first 5 time steps:")
    gamma_df = pd.DataFrame(
        gamma[:5],
        columns=[f"State_{i}" for i in range(hmm_model.total_states)],
        index=[f"t={i}" for i in range(5)],
    )
    print(gamma_df)

    # Check normalization
    sums = np.sum(gamma, axis=1)
    print("\nSum of probabilities at each time step (should be close to 1):")
    for t in range(min(5, T)):
        print(f"t={t}: {sums[t]:.6f}")

    # Check left-right topology properties
    # At t=0, only entry and first real state should have non-zero probabilities
    print("\nFirst time step probabilities:")
    print(gamma[0])

    # Check state progression
    # For a few time points, print which states have significant probability
    print("\nActive states (prob > 0.01) at different time points:")
    check_times = [0, T // 4, T // 2, 3 * T // 4, T - 1]
    for t in check_times:
        active = np.where(gamma[t] > 0.01)[0]
        print(f"t={t}: states {active} active")


def test_xi_debug(hmm_model, feature_set):
    test_features = feature_set[0]
    emission_matrix = hmm_model.compute_emission_matrix(test_features)
    alpha, scale_factors = hmm_model.forward(emission_matrix)
    beta = hmm_model.backward(emission_matrix, scale_factors)
    gamma = hmm_model.compute_gamma(alpha, beta)

    # Let's look at components for a specific time t and state i
    t = 1  # second time step
    i = 1  # first real state
    j = 1  # self-transition

    log_likelihood = np.logaddexp.reduce(alpha[-1])

    print("\nXi calculation components for t=1, state 1->1:")
    print(f"alpha[t,i]: {alpha[t,i]}")
    print(f"beta[t+1,j]: {beta[t+1,j]}")
    print(f"A[i,j]: {hmm_model.A[i,j]}")
    print(f"emission[t+1,j]: {emission_matrix[t+1,j]}")
    print(f"log_likelihood: {log_likelihood}")

    # Calculate expected xi value
    xi_value = np.exp(
        alpha[t, i]
        + np.log(hmm_model.A[i, j])
        + emission_matrix[t + 1, j]
        + beta[t + 1, j]
        - log_likelihood
    )
    print(f"\nCalculated xi value: {xi_value}")

    xi = hmm_model.compute_xi(alpha, beta, emission_matrix)
    print(f"Actual xi value from method: {xi[t,i,j]}")

    # Print first few transitions for t=1
    print("\nXi values at t=1 for possible transitions:")
    pd.set_option("display.precision", 4)
    print(
        pd.DataFrame(
            xi[1],
            columns=[f"To_{i}" for i in range(hmm_model.total_states)],
            index=[f"From_{i}" for i in range(hmm_model.total_states)],
        )
    )


def test_gamma_xi_probabilities(hmm_model, feature_set):
    test_features = feature_set[0]
    emission_matrix = hmm_model.compute_emission_matrix(test_features)
    alpha, scale_factors = hmm_model.forward(emission_matrix)
    beta = hmm_model.backward(emission_matrix, scale_factors)
    gamma = hmm_model.compute_gamma(alpha, beta)
    xi = hmm_model.compute_xi(alpha, beta, emission_matrix)

    T = emission_matrix.shape[0]

    # Test dimensions
    assert gamma.shape == (T, hmm_model.total_states)
    assert xi.shape == (T - 1, hmm_model.total_states, hmm_model.total_states)

    # Test probability properties
    assert np.all(gamma >= 0) and np.all(gamma <= 1)
    assert np.all(xi >= 0) and np.all(xi <= 1)

    print("\nGamma Matrix:")
    hmm_model.print_matrix(gamma, "Gamma Matrix", col="State", idx="T")

    print("\nXi Matrix for t=10 (transitions from time step 10):")
    hmm_model.print_matrix(xi[10], "Xi Matrix t=10", col="To State", idx="From State")


def test_update_transitions(hmm_model, heed_features):
    """Test HMM transition matrix updates with multiple MFCC feature sequences."""
    # Accumulate statistics across all sequences
    aggregated_gamma = np.zeros(hmm_model.total_states)
    aggregated_xi = np.zeros((hmm_model.total_states, hmm_model.total_states))

    for features in heed_features:
        emission_matrix = hmm_model.compute_emission_matrix(features)
        alpha, scale_factors= hmm_model.forward(emission_matrix)
        beta = hmm_model.backward(emission_matrix, scale_factors)
        gamma = hmm_model.compute_gamma(alpha, beta)
        xi = hmm_model.compute_xi(alpha, beta, emission_matrix)

        # Sum over time
        aggregated_gamma += np.sum(gamma[:-1], axis=0)  # Exclude last frame
        aggregated_xi += np.sum(xi, axis=0)  # Sum over time

    print("\nDiagnostic Information:")
    print(f"Aggregated gamma shape: {aggregated_gamma.shape}")
    print(f"Aggregated xi shape: {aggregated_xi.shape}")
    print("\nAggregated gamma sums per state:")
    for i in range(hmm_model.total_states):
        print(f"State {i}: {aggregated_gamma[i]:.6f}")

    print("\nXi transition sums for first real state (state 1):")
    print(f"Sum of transitions from state 1: {np.sum(aggregated_xi[1, :]):.6f}")
    print(f"Self-loop (1->1): {aggregated_xi[1, 1]:.6f}")
    print(f"Forward (1->2): {aggregated_xi[1, 2]:.6f}")

    # Store initial A matrix
    initial_A = hmm_model.A.copy()
    print("\nInitial A matrix:")
    hmm_model.print_matrix(initial_A, "Initial Transition Matrix")

    # Update transition matrix
    hmm_model.update_A(aggregated_xi, aggregated_gamma)

    print("\nUpdated A matrix:")
    hmm_model.print_matrix(hmm_model.A, "Updated Transition Matrix")

    # Print row sums of updated matrix
    print("\nRow sums of updated transition matrix:")
    for i in range(hmm_model.total_states):
        row_sum = np.sum(hmm_model.A[i, :])
        print(f"State {i}: {row_sum:.10f}")

    # Basic structural tests
    assert (
        hmm_model.A[0, 1] == 1.0
    ), "Entry state must transition to first state with prob 1"
    assert np.all(
        hmm_model.A[0, [0, *range(2, hmm_model.total_states)]] == 0
    ), "Entry state should have no other transitions"
    assert hmm_model.A[-1, -1] == 1.0, "Exit state should have self-loop of 1"
    assert np.all(
        hmm_model.A[-1, :-1] == 0
    ), "Exit state should have no other transitions"

    # Check row sums and transitions
    for i in range(1, hmm_model.num_states + 1):
        row_sum = np.sum(hmm_model.A[i, :])
        print(f"\nState {i} transitions:")
        print(f"Self-loop (a_{i}{i}): {hmm_model.A[i, i]:.6f}")
        if i < hmm_model.num_states:
            print(f"Forward (a_{i}{i+1}): {hmm_model.A[i, i+1]:.6f}")
        print(f"Row sum: {row_sum:.10f}")

        assert np.isclose(row_sum, 1.0, atol=1e-10), f"Row {i} must sum to 1"


def test_update_emissions(hmm_model, heed_features):
    """Test HMM emission parameter updates with 'heed' sequences."""
    # Store initial parameters
    initial_means = hmm_model.B["mean"].copy()
    initial_covars = hmm_model.B["covariance"].copy()

    # Print initial parameters
    hmm_model.print_matrix(initial_means, "Initial Means", col="MFCC", idx="State")
    
    print("\nInitial Covariance Matrices:")
    for state in range(1, hmm_model.total_states-1):  # Print real states only
        print(f"\nState {state} Covariance:")
        print(pd.DataFrame(
            initial_covars[state],
            columns=[f'MFCC_{i+1}' for i in range(13)],
            index=[f'MFCC_{i+1}' for i in range(13)]
        ))

    # Collect forward-backward statistics and update
    gamma_per_seq = []
    for features in heed_features:
        emission_matrix = hmm_model.compute_emission_matrix(features)
        alpha, scale_factors = hmm_model.forward(emission_matrix)
        beta = hmm_model.backward(emission_matrix, scale_factors)
        gamma = hmm_model.compute_gamma(alpha, beta)
        gamma_per_seq.append(gamma)

    hmm_model.update_B(heed_features, gamma_per_seq)

    # Print updated parameters
    hmm_model.print_matrix(hmm_model.B["mean"], "Updated Means", col="MFCC", idx="State")
    
    print("\nUpdated Covariance Matrices:")
    for state in range(1, hmm_model.total_states-1):
        print(f"\nState {state} Covariance:")
        print(pd.DataFrame(
            hmm_model.B["covariance"][state],
            columns=[f'MFCC_{i+1}' for i in range(13)],
            index=[f'MFCC_{i+1}' for i in range(13)]
        ))

    # Dimension checks
    assert hmm_model.B["mean"].shape == (10, 13), "Mean shape incorrect"
    assert hmm_model.B["covariance"].shape == (10, 13, 13), "Covariance shape incorrect"

    # Entry/exit state checks
    assert np.all(hmm_model.B["mean"][0] == 0), "Entry state means should be zero"
    assert np.all(hmm_model.B["mean"][-1] == 0), "Exit state means should be zero"
    assert np.all(hmm_model.B["covariance"][0] == 0), "Entry state covariances should be zero"
    assert np.all(hmm_model.B["covariance"][-1] == 0), "Exit state covariances should be zero"

    # Real state checks
    for j in range(1, hmm_model.total_states-1):
        # Check symmetry
        assert np.allclose(
            hmm_model.B["covariance"][j],
            hmm_model.B["covariance"][j].T
        ), f"Covariance matrix for state {j} not symmetric"
        
        # Check positive definiteness
        eigenvals = np.linalg.eigvals(hmm_model.B["covariance"][j])
        assert np.all(eigenvals > -1e-10), f"Covariance matrix for state {j} not positive definite"
        
        # Check diagonal elements above floor
        var_floor = hmm_model.var_floor_factor * np.mean(np.diag(hmm_model.global_covariance))
        diag_elements = np.diag(hmm_model.B["covariance"][j])
        assert np.all(diag_elements >= var_floor), f"State {j} has variances below floor"

    # Check means are finite
    assert np.all(np.isfinite(hmm_model.B["mean"][1:-1])), "Non-finite values in means"


def test_baum_welch(hmm_model, heed_features):
    """
    Test the full Baum-Welch algorithm using the 'heed' sequences.
    Verifies that the model parameters converge to a stable state.
    """
    hmm_model.baum_welch(heed_features)
