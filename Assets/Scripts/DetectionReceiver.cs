using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

[Serializable]
public class DetectionMessage
{
    public string label;

    public float turnDegrees;
}

public class DetectionReceiver : MonoBehaviour
{
    [Header("Dinosaur")]
    [SerializeField]
    private DinosaurReaction dinosaurReaction;

    [Header("UDP")]
    [SerializeField]
    private int port = 5052;

    private UdpClient udpClient;
    private Thread receiveThread;

    private readonly object messageLock =
        new object();

    private DetectionMessage pendingMessage;

    private volatile bool isRunning;

    private void Start()
    {
        if (dinosaurReaction == null)
        {
            Debug.LogError(
                "Assign the dinosaur to DetectionReceiver."
            );

            return;
        }

        StartReceiver();
    }

    private void StartReceiver()
    {
        try
        {
            udpClient = new UdpClient(port);

            isRunning = true;

            receiveThread =
                new Thread(ReceiveMessages);

            receiveThread.IsBackground = true;
            receiveThread.Start();

            Debug.Log(
                $"Listening for Python on UDP port {port}"
            );
        }
        catch (Exception exception)
        {
            Debug.LogException(exception);
        }
    }

    private void ReceiveMessages()
    {
        IPEndPoint remoteEndpoint =
            new IPEndPoint(
                IPAddress.Any,
                0
            );

        while (isRunning)
        {
            try
            {
                byte[] data =
                    udpClient.Receive(
                        ref remoteEndpoint
                    );

                string json =
                    Encoding.UTF8.GetString(data);

                DetectionMessage message =
                    JsonUtility.FromJson<DetectionMessage>(
                        json
                    );

                if (
                    message == null ||
                    string.IsNullOrWhiteSpace(
                        message.label
                    )
                )
                {
                    continue;
                }

                lock (messageLock)
                {
                    pendingMessage = message;
                }
            }
            catch (SocketException)
            {
                if (!isRunning)
                {
                    return;
                }
            }
            catch (ObjectDisposedException)
            {
                return;
            }
            catch (Exception)
            {
                // Keep the receiver thread alive.
            }
        }
    }

    private void Update()
    {
        DetectionMessage message = null;

        lock (messageLock)
        {
            if (pendingMessage != null)
            {
                message = pendingMessage;
                pendingMessage = null;
            }
        }

        if (message == null)
        {
            return;
        }

        string label =
            message.label.Trim();

        Debug.Log(
            $"Unity received object: {label}"
        );

        dinosaurReaction.ReactToObject(label, message.turnDegrees);
    }

    private void OnDestroy()
    {
        StopReceiver();
    }

    private void OnApplicationQuit()
    {
        StopReceiver();
    }

    private void StopReceiver()
    {
        isRunning = false;

        if (udpClient != null)
        {
            udpClient.Close();
            udpClient = null;
        }

        if (
            receiveThread != null &&
            receiveThread.IsAlive
        )
        {
            receiveThread.Join(500);
        }

        receiveThread = null;
    }
}