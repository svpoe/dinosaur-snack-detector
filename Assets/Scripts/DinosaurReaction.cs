using System.Collections;
using UnityEngine;
using TMPro;
using UnityEngine.UI;

public class DinosaurReaction : MonoBehaviour
{
    [Header("Movement")]
    [SerializeField]
    private float forwardDistance = 1.5f;

    [SerializeField]
    private float moveDuration = 1f;

    [SerializeField]
    private float pauseBeforeReturning = 1f;

    [SerializeField]
    private float turnDuration = 0.35f;

    [SerializeField]
    private float maxTurnClamp = 60f;

    [Header("Thought Bubble")]
    [SerializeField]
    private Vector3 thoughtBubbleOffset = new Vector3(0f, 0.45f, 0f);

    [SerializeField]
    private Vector2 thoughtBubbleSize = new Vector2(260f, 110f);

    [SerializeField]
    private float thoughtBubbleScale = 0.01f;

    [SerializeField]
    private Color thoughtBubbleBackgroundColor = new Color(1f, 1f, 1f, 0.9f);

    [SerializeField]
    private Color thoughtBubbleTextColor = new Color(0.1f, 0.1f, 0.1f, 1f);

    private AudioSource audioSource;
    private bool isReacting;

    private Vector3 startingPosition;
    private Quaternion startingRotation;

    private Canvas thoughtBubbleCanvas;
    private TextMeshProUGUI thoughtBubbleText;
    private Camera mainCamera;
    private Renderer[] cachedRenderers;

    private void Start()
    {
        audioSource = GetComponent<AudioSource>();

        startingPosition = transform.position;
        startingRotation = transform.rotation;
        cachedRenderers = GetComponentsInChildren<Renderer>();

        mainCamera = Camera.main;
        CreateThoughtBubble();
    }

    public void ReactToObject(string objectName, float turnDegrees)
    {
        if (isReacting)
        {
            return;
        }

        Debug.Log(
            $"Dinosaur reacting to: {objectName}"
        );

        ShowThoughtBubble(objectName);

        StartCoroutine(
            ReactionSequence(turnDegrees)
        );
    }

    private IEnumerator ReactionSequence(float turnDegrees)
    {
        isReacting = true;

        float clampedTurnDegrees =
            Mathf.Clamp(
                turnDegrees,
                -maxTurnClamp,
                maxTurnClamp
            );

        Quaternion targetRotation =
            startingRotation *
            Quaternion.Euler(0f, clampedTurnDegrees, 0f);

        Vector3 forwardPosition =
            startingPosition +
            targetRotation *
            Vector3.forward * forwardDistance;

        // Turn in place toward the detected object.
        yield return StartCoroutine(
            RotateTo(
                targetRotation,
                turnDuration
            )
        );

        // Walk forward.
        yield return StartCoroutine(
            MoveTo(
                forwardPosition,
                moveDuration
            )
        );

        // Make sound.
        if (
            audioSource != null &&
            audioSource.clip != null
        )
        {
            audioSource.Play();
        }
        else
        {
            Debug.LogWarning(
                "No AudioSource or audio clip assigned."
            );
        }

        yield return new WaitForSeconds(
            pauseBeforeReturning
        );

        // Turn around before walking back.
        yield return StartCoroutine(
            RotateTo(
                targetRotation *
                Quaternion.Euler(0f, 180f, 0f),
                turnDuration
            )
        );

        // Return to starting position.
        yield return StartCoroutine(
            MoveTo(
                startingPosition,
                moveDuration
            )
        );

        transform.position = startingPosition;

        // Slowly rotate back to the original facing direction.
        yield return StartCoroutine(
            RotateTo(
                startingRotation,
                turnDuration
            )
        );

        HideThoughtBubble();

        isReacting = false;
    }

    private void LateUpdate()
    {
        if (
            thoughtBubbleCanvas == null ||
            !thoughtBubbleCanvas.gameObject.activeSelf
        )
        {
            return;
        }

        if (mainCamera == null)
        {
            mainCamera = Camera.main;
        }

        if (mainCamera == null)
        {
            return;
        }

        UpdateThoughtBubblePosition();

        Vector3 toCamera =
            thoughtBubbleCanvas.transform.position -
            mainCamera.transform.position;

        thoughtBubbleCanvas.transform.rotation =
            Quaternion.LookRotation(toCamera);
    }

    private void CreateThoughtBubble()
    {
        GameObject canvasObject = new GameObject("ThoughtBubble");
        canvasObject.transform.SetParent(transform, false);
        canvasObject.transform.localRotation = Quaternion.identity;
        canvasObject.transform.localScale = Vector3.one * thoughtBubbleScale;

        thoughtBubbleCanvas = canvasObject.AddComponent<Canvas>();
        thoughtBubbleCanvas.renderMode = RenderMode.WorldSpace;
        thoughtBubbleCanvas.sortingOrder = 1000;

        RectTransform canvasRect =
            canvasObject.GetComponent<RectTransform>();

        canvasRect.sizeDelta = thoughtBubbleSize;

        GameObject panelObject = new GameObject("BubbleBackground");
        panelObject.transform.SetParent(canvasObject.transform, false);

        Image background = panelObject.AddComponent<Image>();
        background.sprite = CreateSolidSprite();
        background.color = thoughtBubbleBackgroundColor;

        RectTransform panelRect =
            panelObject.GetComponent<RectTransform>();

        panelRect.anchorMin = Vector2.zero;
        panelRect.anchorMax = Vector2.one;
        panelRect.offsetMin = Vector2.zero;
        panelRect.offsetMax = Vector2.zero;

        GameObject textObject = new GameObject("BubbleText");
        textObject.transform.SetParent(panelObject.transform, false);

        thoughtBubbleText = textObject.AddComponent<TextMeshProUGUI>();
        thoughtBubbleText.alignment = TextAlignmentOptions.Center;
        thoughtBubbleText.enableAutoSizing = true;
        thoughtBubbleText.fontSizeMin = 18;
        thoughtBubbleText.fontSizeMax = 42;
        thoughtBubbleText.color = thoughtBubbleTextColor;
        thoughtBubbleText.text = string.Empty;

        RectTransform textRect =
            textObject.GetComponent<RectTransform>();

        textRect.anchorMin = new Vector2(0.08f, 0.12f);
        textRect.anchorMax = new Vector2(0.92f, 0.88f);
        textRect.offsetMin = Vector2.zero;
        textRect.offsetMax = Vector2.zero;

        thoughtBubbleCanvas.gameObject.SetActive(false);
        UpdateThoughtBubblePosition();
    }

    private void ShowThoughtBubble(string objectName)
    {
        if (thoughtBubbleText == null || thoughtBubbleCanvas == null)
        {
            return;
        }

        thoughtBubbleText.text = $"Yum, {objectName}";
        UpdateThoughtBubblePosition();
        thoughtBubbleCanvas.gameObject.SetActive(true);
    }

    private void HideThoughtBubble()
    {
        if (thoughtBubbleCanvas != null)
        {
            thoughtBubbleCanvas.gameObject.SetActive(false);
        }
    }

    private Sprite CreateSolidSprite()
    {
        Texture2D texture = new Texture2D(1, 1, TextureFormat.RGBA32, false);
        texture.SetPixel(0, 0, Color.white);
        texture.Apply();

        return Sprite.Create(
            texture,
            new Rect(0f, 0f, 1f, 1f),
            new Vector2(0.5f, 0.5f),
            1f
        );
    }

    private void UpdateThoughtBubblePosition()
    {
        if (thoughtBubbleCanvas == null)
        {
            return;
        }

        Vector3 bubblePosition = transform.position + thoughtBubbleOffset;

        if (cachedRenderers != null && cachedRenderers.Length > 0)
        {
            Bounds combinedBounds = cachedRenderers[0].bounds;

            for (int index = 1; index < cachedRenderers.Length; index++)
            {
                combinedBounds.Encapsulate(cachedRenderers[index].bounds);
            }

            bubblePosition = new Vector3(
                combinedBounds.center.x,
                combinedBounds.max.y,
                combinedBounds.center.z
            ) + thoughtBubbleOffset;
        }

        thoughtBubbleCanvas.transform.position = bubblePosition;
    }

    private IEnumerator MoveTo(
        Vector3 destination,
        float duration
    )
    {
        Vector3 startPosition = transform.position;

        float elapsed = 0f;

        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;

            float progress =
                Mathf.Clamp01(
                    elapsed / duration
                );

            transform.position =
                Vector3.Lerp(
                    startPosition,
                    destination,
                    progress
                );

            yield return null;
        }

        transform.position = destination;
    }

    private IEnumerator RotateTo(
        Quaternion destination,
        float duration
    )
    {
        Quaternion startRotation = transform.rotation;

        float elapsed = 0f;

        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;

            float progress =
                Mathf.Clamp01(
                    elapsed / duration
                );

            transform.rotation =
                Quaternion.Slerp(
                    startRotation,
                    destination,
                    progress
                );

            yield return null;
        }

        transform.rotation = destination;
    }
}